#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <libzbd/zbd.h>

/**
 * Write one request-sized page at zone start.
 */
static ssize_t write_one_page_to_zone(int fd, const struct zbd_zone *zone, size_t request_size) {
    void *buffer = NULL;

    if (posix_memalign(&buffer, request_size, request_size) != 0) {
        perror("posix_memalign");
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
static int reset_zone(int fd, const struct zbd_zone *zone) {
    int ret = zbd_reset_zones(fd, zone->start, zone->len);
    if (ret < 0) {
        fprintf(stderr, "❌ reset failed at 0x%llx: %s\n",
                (unsigned long long)zone->start, strerror(errno));
    }
    return ret;
}

/* ---------------------------
 * Thread worker
 * --------------------------- */

typedef struct {
    const char *dev_path;
    size_t req_size;
    int zone_idx;
    struct zbd_zone zone_copy;

    int did_write;
    int did_reset;
} zone_task_t;

static void *zone_worker(void *arg) {
    zone_task_t *t = (zone_task_t *)arg;

    // Open per-thread fd for clean isolation.
    struct zbd_info info;
    int fd = zbd_open(t->dev_path, O_WRONLY | O_DIRECT, &info);
    if (fd < 0) {
        fprintf(stderr, "❌ [t=%d zone=%d] zbd_open failed: %s\n",
                t->zone_idx, t->zone_idx, strerror(errno));
        t->did_write = 0;
        t->did_reset = 0;
        return NULL;
    }

    // Write one page at zone start
    ssize_t written = write_one_page_to_zone(fd, &t->zone_copy, t->req_size);
    if (written > 0) {
        printf("✅ [zone %d] wrote %zd bytes at 0x%llx\n",
               t->zone_idx, written, (unsigned long long)t->zone_copy.start);
        t->did_write = 1;
    } else {
        printf("❌ [zone %d] write failed at 0x%llx\n",
               t->zone_idx, (unsigned long long)t->zone_copy.start);
        t->did_write = 0;
    }

    // Reset the zone if write succeeded
    if (t->did_write && reset_zone(fd, &t->zone_copy) == 0) {
        printf("♻️  [zone %d] reset ok at 0x%llx\n",
               t->zone_idx, (unsigned long long)t->zone_copy.start);
        t->did_reset = 1;
    } else {
        t->did_reset = 0;
    }

    zbd_close(fd);
    return NULL;
}

int main(int argc, char *argv[]) {
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <device> <request_size> <parallel_zones>\n", argv[0]);
        fprintf(stderr, "Example: %s /dev/nvme0n1 4096 8\n", argv[0]);
        return EXIT_FAILURE;
    }

    const char *dev_path = argv[1];
    size_t req_size = strtoull(argv[2], NULL, 10);
    int parallel = atoi(argv[3]);

    if (req_size == 0) {
        fprintf(stderr, "❌ request_size must be > 0\n");
        return EXIT_FAILURE;
    }
    if (parallel <= 0) {
        fprintf(stderr, "❌ parallel_zones must be > 0\n");
        return EXIT_FAILURE;
    }

    // List zones once (single fd just for listing)
    struct zbd_info info;
    int fd_list = zbd_open(dev_path, O_WRONLY | O_DIRECT, &info);
    if (fd_list < 0) {
        perror("zbd_open");
        return EXIT_FAILURE;
    }

    struct zbd_zone *zones = NULL;
    unsigned int nr_zones = 0;
    if (zbd_list_zones(fd_list, 0, 0, ZBD_RO_ALL, &zones, &nr_zones) < 0) {
        perror("zbd_list_zones");
        zbd_close(fd_list);
        return EXIT_FAILURE;
    }
    zbd_close(fd_list);

    if ((unsigned int)parallel > nr_zones) {
        fprintf(stderr, "❌ parallel_zones=%d but device has only %u zones\n", parallel, nr_zones);
        free(zones);
        return EXIT_FAILURE;
    }

    printf("ℹ️  launching exactly %d threads for zones [0..%d]\n", parallel, parallel - 1);

    pthread_t *threads = calloc(parallel, sizeof(pthread_t));
    zone_task_t *tasks = calloc(parallel, sizeof(zone_task_t));
    if (!threads || !tasks) {
        perror("calloc");
        free(threads);
        free(tasks);
        free(zones);
        return EXIT_FAILURE;
    }

    // Create exactly `parallel` threads: thread i -> zone i
    for (int i = 0; i < parallel; i++) {
        struct zbd_zone *z = &zones[i];

        // If you want to *hard fail* on non-seq zones, change this to exit.
        if (!zbd_zone_seq(z)) {
            printf("⚠️  zone %d is not sequential; skipping thread creation for it\n", i);
            tasks[i].did_write = 0;
            tasks[i].did_reset = 0;
            continue;
        }

        tasks[i].dev_path = dev_path;
        tasks[i].req_size = req_size;
        tasks[i].zone_idx = i;
        tasks[i].zone_copy = *z;
        tasks[i].did_write = 0;
        tasks[i].did_reset = 0;

        int rc = pthread_create(&threads[i], NULL, zone_worker, &tasks[i]);
        if (rc != 0) {
            fprintf(stderr, "❌ pthread_create failed for zone %d: %s\n", i, strerror(rc));
        }
    }

    // Join threads that were actually created
    int wrote_ok = 0, reset_ok = 0;
    for (int i = 0; i < parallel; i++) {
        // If thread wasn't created, pthread_t will be 0 on many platforms,
        // but that isn't guaranteed. We track by checking if zone was sequential.
        if (!zbd_zone_seq(&zones[i])) {
            continue;
        }
        pthread_join(threads[i], NULL);
        wrote_ok += tasks[i].did_write;
        reset_ok += tasks[i].did_reset;
    }

    printf("✅ done: threads=%d, wrote_ok=%d, reset_ok=%d\n", parallel, wrote_ok, reset_ok);

    free(threads);
    free(tasks);
    free(zones);
    return EXIT_SUCCESS;
}
