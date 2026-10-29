#!/usr/bin/env python3
"""Run the real installer request handler with stubbed HTTP and PS5 services."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MHD_HEADER = r'''
#include <stddef.h>
enum MHD_Result { MHD_NO, MHD_YES };
enum MHD_ResponseMemoryMode { MHD_RESPMEM_PERSISTENT, MHD_RESPMEM_MUST_FREE };
enum MHD_ValueKind { MHD_GET_ARGUMENT_KIND, MHD_HEADER_KIND };
struct MHD_Connection { const char *action; };
struct MHD_Response { int unused; };
#define MHD_HTTP_OK 200
#define MHD_HTTP_FORBIDDEN 403
#define MHD_HTTP_NOT_FOUND 404
#define MHD_HTTP_METHOD_NOT_ALLOWED 405
#define MHD_HTTP_INTERNAL_SERVER_ERROR 500
#define MHD_HTTP_SERVICE_UNAVAILABLE 503
struct MHD_Response *MHD_create_response_from_buffer(size_t, void *, enum MHD_ResponseMemoryMode);
int MHD_add_response_header(struct MHD_Response *, const char *, const char *);
enum MHD_Result MHD_queue_response(struct MHD_Connection *, unsigned int, struct MHD_Response *);
void MHD_destroy_response(struct MHD_Response *);
const char *MHD_lookup_connection_value(struct MHD_Connection *, enum MHD_ValueKind, const char *);
'''
HARNESS = r'''
#include <assert.h>
#include <stdarg.h>
#include <string.h>
#include "http_server.h"
#include "file_registry.h"
static unsigned int status;
static int clears, installs;
static struct MHD_Response response;
struct MHD_Response *MHD_create_response_from_buffer(size_t n, void *p, enum MHD_ResponseMemoryMode m) { return &response; }
int MHD_add_response_header(struct MHD_Response *r, const char *k, const char *v) { return 1; }
enum MHD_Result MHD_queue_response(struct MHD_Connection *c, unsigned int code, struct MHD_Response *r) { status = code; return MHD_YES; }
void MHD_destroy_response(struct MHD_Response *r) {}
const char *MHD_lookup_connection_value(struct MHD_Connection *c, enum MHD_ValueKind kind, const char *name) {
    return kind == MHD_HEADER_KIND && !strcmp(name, "X-WKRLI-Action") ? c->action : NULL;
}
const FileEntry *file_registry_find(const char *url) { return NULL; }
int installer_install_app_if_needed(void) { installs++; return 0; }
int installer_clear_webkit_data(void) { clears++; return 0; }
void installer_log(const char *fmt, ...) {}
size_t installer_wait_logs(size_t *pos, char *buf, size_t n) { return 0; }
int sceUserServiceGetForegroundUser(int *uid) { *uid = 42; return 0; }
int puff(unsigned char *dest, unsigned long *destlen, const unsigned char *src, unsigned long *srclen) { return -1; }
static void request(const char *url, const char *method, const char *action) {
    struct MHD_Connection conn = { action };
    void *session = (void *)1; size_t upload_size = 0;
    assert(http_on_request(NULL, &conn, url, method, "HTTP/1.1", NULL, &upload_size, &session) == MHD_YES);
}
int main(void) {
    const char *routes[] = { "/clear-webkit-data", "/install", "/exit" };
    for (unsigned int i = 0; i < 3; i++) {
        request(routes[i], "GET", NULL); assert(status == 405);
        request(routes[i], "POST", NULL); assert(status == 403);
        request(routes[i], "POST", "wrong"); assert(status == 403);
    }
    assert(clears == 0 && installs == 0);
    request("/clear-webkit-data", "POST", "clear-webkit-data");
    assert(status == 200 && clears == 1);
    request("/install", "POST", "install");
    assert(status == 200 && installs == 1);
    request("/exit", "POST", "exit"); assert(status == 200);
    return 0;
}
'''


class InstallerHttpTest(unittest.TestCase):
    def test_mutations_require_post_and_action_header(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('A C compiler is required for the installer handler test')
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'microhttpd.h').write_text('#pragma once\n' + MHD_HEADER)
            (work / 'wkrli_version.h').write_text('#define WKRLI_FULL_VERSION "test"\n')
            (work / 'file_registry.h').write_text(
                '#pragma once\n#include <stddef.h>\n'
                'typedef struct { const unsigned char *data; size_t size, orig_size; '
                'int compressed; const char *content_type; } FileEntry;\n'
                'const FileEntry *file_registry_find(const char *);\n')
            (work / 'test.c').write_text(HARNESS)
            result = subprocess.run([compiler, '-std=c11', '-Wall', '-Werror', '-I' + str(work),
                            '-I' + str(ROOT / 'installer/include'),
                            '-I' + str(ROOT / 'installer/common'), str(work / 'test.c'),
                            str(ROOT / 'installer/src/http_server.c'), '-o', str(work / 'test')],
                           capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(work / 'test')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
