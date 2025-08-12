#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <libzbd/zbd.h>

/**
 * Round up value `n` to the nearest multiple of `align`.
 */
static size_t round_up(size_t n, size_t align) {
    return ((n + align - 1) / align) * align;
}

/**
 * @brief Write percentage of a zone using synchronous direct I/O.
 */
ssize_t write_zone_percentage(int fd, struct zbd_zone *zone, size_t block_size,
                              size_t request_size, double pct) {
    if (pct <= 0 || pct > 100) {
        fprintf(stderr, "Invalid percentage: %f%%\n", pct);
        return -1;
    }

    size_t bytes_raw = (pct * zone->capacity) / 100;
    size_t bytes_to_write = round_up(bytes_raw, request_size);  // align to 4 KiB or req_size
    off_t wp = zone->start;

    printf("zone capacity %llu, raw bytes %lu, aligned bytes to write %lu\n",
           zone->capacity, bytes_raw, bytes_to_write);

    void *buffer;
    if (posix_memalign(&buffer, request_size, request_size) != 0) {
        perror("posix_memalign failed");
        return -1;
    }
    memset(buffer, 0xAC, request_size);

    size_t written = 0;
    while (written < bytes_to_write) {
        ssize_t ret = pwrite(fd, buffer, request_size, wp + written);
        if (ret < 0) {
            perror("pwrite");
            free(buffer);
            return -1;
        }
        written += ret;
    }

    printf("Zone at offset 0x%llx: Wrote approx. %.6f%% (%zu bytes)\n",
        (unsigned long long)zone->start, pct, written);

    free(buffer);
    return written;
}

/**
 * @brief Finish the zone and measure latency.
 */
double finish_zone_and_record(int fd, struct zbd_zone *zone, size_t block_size) {
    struct timespec start, end;
    off_t byte_offset = zone->start;
    size_t length = zone->capacity;

    clock_gettime(CLOCK_MONOTONIC, &start);
    if (zbd_finish_zones(fd, byte_offset, length) != 0) {
        perror("zbd_finish_zones failed");
        return -1.0;
    }
    clock_gettime(CLOCK_MONOTONIC, &end);

    return (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
}


int main(int argc, char *argv[]) {
    if (argc < 5) {
        fprintf(stderr, "Usage: %s <device> <request_size> <result_file> <pct1> [pct2 pct3 ...]\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *dev_path = argv[1];
    size_t req_size = strtoull(argv[2], NULL, 10);
    const char *result_file = argv[3];

    struct zbd_info info;
    int fd = zbd_open(dev_path, O_WRONLY | O_DIRECT, &info);
    if (fd < 0) {
        perror("zbd_open");
        return EXIT_FAILURE;
    }

    struct zbd_zone *zones;
    unsigned int nr_zones;
    if (zbd_list_zones(fd, 0, 0, ZBD_RO_ALL, &zones, &nr_zones) < 0) {
        perror("zbd_list_zones");
        zbd_close(fd);
        return EXIT_FAILURE;
    }

    FILE *log = fopen(result_file, "a");
    if (!log) {
        perror("Failed to open result file");
        free(zones);
        zbd_close(fd);
        return EXIT_FAILURE;
    }

    for (int i = 0; i < argc - 4; ++i) {
        double pct = atof(argv[i + 4]);
        if (i >= nr_zones) {
            fprintf(stderr, "No more zones to write (index %d)\n", i);
            break;
        }

        struct zbd_zone *zone = &zones[i];
        if (!zbd_zone_seq(zone)) {
            printf("Skipping non-sequential zone at index %d\n", i);
            continue;
        }

        if (write_zone_percentage(fd, zone, info.lblock_size, req_size, pct) < 0) {
            fprintf(stderr, "Write failed at zone %d\n", i);
            continue;
        }

        double finish_time = finish_zone_and_record(fd, zone, info.lblock_size);
        if (finish_time >= 0) {
            fprintf(log, "zone_%d,%.6f%%,%.6f(s)\n", i, pct, finish_time);
            printf("Zone %d finished in %.6f seconds.\n", i, finish_time);
        } else {
            fprintf(stderr, "Failed to finish zone %d\n", i);
        }
    }

    fclose(log);
    free(zones);
    zbd_close(fd);
    return EXIT_SUCCESS;
}
