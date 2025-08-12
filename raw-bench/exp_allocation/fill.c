#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <libzbd/zbd.h>
#include <math.h>

/**
 * Write one request-sized page at zone start.
 */
ssize_t write_one_page_to_zone(int fd, struct zbd_zone *zone, size_t request_size) {
    void *buffer;
    if (posix_memalign(&buffer, request_size, request_size) != 0) {
        perror("posix_memalign failed");
        return -1;
    }
    memset(buffer, 0xAC, request_size);

    ssize_t ret = pwrite(fd, buffer, request_size, zone->start);
    if (ret < 0) {
        perror("pwrite");
    }

    free(buffer);
    return ret;
}

/**
 * Reset the zone using libzbd.
 */
int reset_zone(int fd, struct zbd_zone *zone) {
    int ret = zbd_reset_zones(fd, zone->start, zone->len);
    if (ret < 0) {
        fprintf(stderr, "❌ Failed to reset zone at 0x%llx: %s\n",
                (unsigned long long)zone->start, strerror(errno));
    }
    return ret;
}

int main(int argc, char *argv[]) {
    if (argc != 5) {
        fprintf(stderr, "Usage: %s <device> <request_size> <result_file> <percentage>\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *dev_path = argv[1];
    size_t req_size = strtoull(argv[2], NULL, 10);
    const char *result_file = argv[3];
    int pct = atoi(argv[4]);

    if (pct <= 0 || pct > 100) {
        fprintf(stderr, "❌ Invalid percentage: %d%%\n", pct);
        return EXIT_FAILURE;
    }

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

    int zones_to_write = (int)ceil(nr_zones * (pct / 100.0));
    printf("ℹ️  Writing to first %d of %u zones (%d%%)\n", zones_to_write, nr_zones, pct);

    int *written_zone_indices = calloc(zones_to_write, sizeof(int));
    if (!written_zone_indices) {
        perror("calloc failed");
        free(zones);
        zbd_close(fd);
        return EXIT_FAILURE;
    }

    int written_count = 0;

    for (int i = 0; i < zones_to_write; i++) {
        struct zbd_zone *zone = &zones[i];

        if (!zbd_zone_seq(zone)) {
            printf("⚠️  Skipping non-sequential zone %d\n", i);
            continue;
        }

        ssize_t written = write_one_page_to_zone(fd, zone, req_size);
        if (written > 0) {
            printf("✅ Zone %d at 0x%llx: Wrote %zd bytes\n",
                   i, (unsigned long long)zone->start, written);
            written_zone_indices[written_count++] = i;
        } else {
            printf("❌ Write failed at zone %d\n", i);
        }
    }


    // === RESET STAGE ===
    printf("🔁 Resetting %d zones...\n", written_count);
    for (int i = 0; i < written_count; i++) {
        int idx = written_zone_indices[i];
        struct zbd_zone *zone = &zones[idx];

        if (reset_zone(fd, zone) == 0) {
            printf("♻️  Reset zone %d at offset 0x%llx\n", idx, (unsigned long long)zone->start);
        }
    }

    free(written_zone_indices);
    free(zones);
    zbd_close(fd);

    return EXIT_SUCCESS;
}
