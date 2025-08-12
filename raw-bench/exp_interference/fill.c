#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <libzbd/zbd.h>

/**
 * Round up `n` to the nearest multiple of `align`
 */
static size_t round_up(size_t n, size_t align) {
    return ((n + align - 1) / align) * align;
}

/**
 * @brief Write percentage of a zone using direct I/O with aligned buffer.
 */
ssize_t write_zone_percentage(int fd, struct zbd_zone *zone, size_t block_size,
                              size_t request_size, int pct) {
    if (pct <= 0 || pct > 100) {
        fprintf(stderr, "Invalid percentage: %d%%\n", pct);
        return -1;
    }

    size_t raw_bytes = (pct * zone->capacity) / 100;
    size_t bytes_to_write = round_up(raw_bytes, request_size);
    off_t wp = zone->start;

    printf("zone capacity %llu, raw %lu, aligned to write %lu: ",
           zone->capacity, raw_bytes, bytes_to_write);

    void *buffer;
    if (posix_memalign(&buffer, request_size, request_size) != 0) {
        perror("posix_memalign failed");
        return -1;
    }
    memset(buffer, 0xAC, request_size);  // Dummy data

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

    printf("Zone at offset 0x%llx: Wrote approx. %d%% (%zu bytes)\n",
           (unsigned long long)zone->start, pct, written);
    free(buffer);
    return written;
}

int main(int argc, char *argv[]) {
    if (argc != 6) {
        fprintf(stderr, "Usage: %s <device> <request_size> <zone_index> <result_file> <percentage>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *dev_path = argv[1];
    size_t req_size = strtoull(argv[2], NULL, 10);
    int zone_index = atoi(argv[3]);
    const char *result_file = argv[4];
    int pct = atoi(argv[5]);

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

    if (zone_index >= nr_zones || zone_index < 0) {
        fprintf(stderr, "Invalid zone index %d (max: %u)\n", zone_index, nr_zones - 1);
        free(zones);
        zbd_close(fd);
        return EXIT_FAILURE;
    }

    struct zbd_zone *zone = &zones[zone_index];

    if (!zbd_zone_seq(zone)) {
        printf("Skipping non-sequential zone at index %d\n", zone_index);
        free(zones);
        zbd_close(fd);
        return EXIT_FAILURE;
    }

    ssize_t written = write_zone_percentage(fd, zone, info.lblock_size, req_size, pct);
    if (written < 0) {
        fprintf(stderr, "Write failed at zone %d\n", zone_index);
    } else {
        FILE *log = fopen(result_file, "a");
        if (!log) {
            perror("Failed to open result file");
        } else {
            fprintf(log, "zone_%d,%d%%,%zd\n", zone_index, pct, written);
            fclose(log);
        }
    }

    free(zones);
    zbd_close(fd);
    return EXIT_SUCCESS;
}
