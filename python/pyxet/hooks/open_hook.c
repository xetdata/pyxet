#include <sys/stat.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <sys/errno.h>
#include "interpose.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "subprocess.h"
#ifdef __APPLE__
 #include <mach-o/dyld.h>
#endif
int LOG_OUTPUT_FD = -1;
const char* LOG_FILE = NULL;
bool ENABLE_INTERPOSE = true;
int set_xlog_point(const char* fname);
int close_xlog_point();
int write_xlog(const char* s, size_t len);

/**************************************************************************/
/*                                                                        */
/*                            Stringy Routines                            */
/*                                                                        */
/**************************************************************************/

void strip_terminating_ws(char* s) {
  int len = strlen(s);
  while (len > 0) {
    if (s[len-1] == '\n' || s[len-1] == '\r' || s[len-1] == ' ') {
      --len;
    } else {
      break;
    }
  }
  s[len] = 0;
}

bool str_ends_with(char *str, char* comp) {
  size_t slen = strlen(str);
  size_t clen = strlen(comp);
  if (slen < clen) {
    return false;
  } 
  if (strcmp(str + slen - clen, comp) == 0) {
    return true;
  }
  return false;
}

bool str_starts_with(char *str, char* comp) {
  size_t clen = strlen(comp);
  if (strncmp(str, comp, clen) == 0) {
    return true;
  }
  return false;
}

void replace_char(char *str, char src, char dest) {
  size_t clen = strlen(str);
  for (size_t i = 0;i < clen; ++i) {
    if (str[i] == src) str[i] = dest;
  }
}


/**************************************************************************/
/*                                                                        */
/*                               Git Track                                */
/*                                                                        */
/**************************************************************************/
struct GitPath {
  char* path;
  char* version;
  char* remote;
};

pthread_mutex_t gitpath_cache_lock = PTHREAD_MUTEX_INITIALIZER;
struct GitPath* gitpath_cache = NULL;
size_t gitpath_cache_len = 0;
size_t gitpath_cache_capacity = 0;


extern char **environ;
char*const* SUBPROCESS_ENV = NULL;

/// Environment use to run the git Subprocesses. 
/// Copies environ, but adds XTRACE_DISABLE
char*const* subprocess_env() {
  if (SUBPROCESS_ENV != NULL) {
    return SUBPROCESS_ENV;
  }
  int nenv = 0;
  while(environ[nenv] != NULL) {
      nenv++;
  }
  // we are going to insert an environment variable
  // XTRACE_DISABLE=
  bool env_has_disable = false;
  char **env = malloc(sizeof(char*) * (nenv + 2));
  for (int i = 0;i < nenv; ++i) {
    int elen = strlen(environ[i]);
    env[i] = malloc(elen + 1);
    memcpy(env[i], environ[i], elen + 1); // copy the \0
    if (str_starts_with(env[i], "XTRACE_DISABLE")) {
      env_has_disable = true;
    }
  }
  if (!env_has_disable) {
    env[nenv] = "XTRACE_DISABLE=1";
    env[nenv+1] = NULL;
  } else {
    env[nenv] = NULL;
  }
  SUBPROCESS_ENV = env;
  return SUBPROCESS_ENV;
}

char* get_path_version(const char* path) {
  char* cmd = NULL;
  int cmdlen = asprintf(&cmd, "git -C %s describe --all --always --abbrev=0 --exclude=* 2> /dev/null", path);
  const char* cmdarr[4] = {"sh", "-c", cmd, NULL};
  struct subprocess_s subprocess;
  int result = subprocess_create_ex(cmdarr, subprocess_option_search_user_path | subprocess_option_combined_stdout_stderr, (const char**)subprocess_env(), &subprocess);
  free(cmd);
  if (result != 0) {
    return NULL;
  }

  int process_return;
  if (subprocess_join(&subprocess, &process_return) != 0) {
    subprocess_terminate(&subprocess);
  }
  FILE* subp = subprocess_stdout(&subprocess);
  if (subp == NULL) {
    return NULL;
  }
  char* version = malloc(128);
  char* ret = fgets(version, 128, subp);
  subprocess_destroy(&subprocess);
  if (ret == NULL) {
    free(version);
    return NULL;
  }
  // if ret != NULL, version is a null terminated string
  strip_terminating_ws(version);
  return version;
}

char* sanitize_remote(char* r) {
  // look for https://blah:blah@....
  // and drop everything between https:// and the @ inclusive
  size_t rlen = strlen(r);
  size_t searchlen = 8;
  char* hs = strnstr(r, "https://", rlen);
  if (hs == NULL) {
    searchlen = 7;
    hs = strnstr(r, "http://", rlen);
  }
  if (hs == NULL) {
    return r;
  }
  // shift to the end of the protocol
  hs += searchlen;
  char* at = strchr(hs, '@');
  if (at == NULL) {
    return r;
  }
  at += 1; // we want the start at the byte after the @
  size_t bytes_to_move = r + rlen - at + 1; // +1 to include the NULL ptr
  memmove(hs, at, bytes_to_move); 
  return r;
}


char* get_path_remote(const char* path) {
  char* cmd = NULL;
  int cmdlen = asprintf(&cmd, "git -C %s remote -v 2> /dev/null", path);
  const char* cmdarr[4] = {"sh", "-c", cmd, NULL};
  struct subprocess_s subprocess;
  int result = subprocess_create_ex(cmdarr, subprocess_option_search_user_path | subprocess_option_combined_stdout_stderr, (const char**)subprocess_env(), &subprocess);
  free(cmd);
  if (result != 0) {
    return NULL;
  }

  int process_return;
  if (subprocess_join(&subprocess, &process_return) != 0) {
    subprocess_terminate(&subprocess);
  }
  FILE* subp = subprocess_stdout(&subprocess);
  if (subp == NULL) {
    return NULL;
  }
  char* remote= malloc(128);
  char* ret = fgets(remote, 128, subp);
  subprocess_destroy(&subprocess);
  if (ret == NULL) {
    free(remote);
    return NULL;
  }
  // if ret != NULL, remote is a null terminated string
  strip_terminating_ws(remote);
  // strip the (fetch) and (push)
  // scan forward and NULL the first ' '
  char* sp = strrchr(remote, ' ');
  if (sp != NULL) {
    (*sp) = 0;
  }
  replace_char(remote,'\t',' ');
  return sanitize_remote(remote);
}



struct GitPath get_cached_path_info(const char* path) {
  struct GitPath ret;
  pthread_mutex_lock(&gitpath_cache_lock);
  // search the cache for the entry, return the version if it exists
  for (size_t i = 0; i < gitpath_cache_len; ++i) {
    if (strcmp(gitpath_cache[i].path, path) == 0) {
      ret = gitpath_cache[i];
      pthread_mutex_unlock(&gitpath_cache_lock);
      return ret;
    }
  }
  // clone path
  size_t plen = strlen(path);
  char* newpath = malloc(plen + 1);
  memcpy((void*)newpath, path, plen+ 1);

  pthread_mutex_unlock(&gitpath_cache_lock);
  // not in cache. look it up
  char* version = get_path_version(path);
  char* remote = get_path_remote(path);


  // yes desc can return NULL and we will cache that too
  // relock the cache 
  pthread_mutex_lock(&gitpath_cache_lock);
  // if we do not have capacity, resize and up the capacity
  if (gitpath_cache_capacity < gitpath_cache_len + 1) {
    size_t target_cap = 2 * (gitpath_cache_len + 1);
    gitpath_cache = realloc(gitpath_cache, sizeof(struct GitPath) * target_cap);
    gitpath_cache_capacity = target_cap;
  }
  gitpath_cache[gitpath_cache_len].path = newpath;
  gitpath_cache[gitpath_cache_len].version = version;
  gitpath_cache[gitpath_cache_len].remote = remote;
  ret = gitpath_cache[gitpath_cache_len];
  gitpath_cache_len++;
  pthread_mutex_unlock(&gitpath_cache_lock);
  return ret;
}

char* get_parent_path(const char* path) {
  char* abspath = realpath(path, NULL);
  if (abspath == NULL) {
    return NULL;
  }
  char* sp = strrchr(abspath, '/');
  if (sp != NULL) {
    (*sp) = 0;
  }
  return abspath;
}

/**************************************************************************/
/*                                                                        */
/*                             Open Interpose                             */
/*                                                                        */
/**************************************************************************/
static int internal_open(const char *pathname, int flags, mode_t mode);
static FILE* internal_fopen(const char * restrict path, const char * restrict mode);
static int internal_rename(const char* src, const char* dest);


INTERPOSE_C(int, open, (const char* pathname, int flags, mode_t mode), (pathname, flags, mode)) {
  return internal_open(pathname, flags, mode);
}


INTERPOSE_C(FILE*, fopen, (const char* restrict path, const char* restrict mode), (path, mode)) {
  return internal_fopen(path, mode);
}

int internal_open(const char *pathname, int flags, mode_t mode){
  int ret = Real__open(pathname, flags, mode);
  if (ENABLE_INTERPOSE == false) {
    return ret;
  }
  if (strncmp(pathname, "/bin", 4) == 0 || strncmp(pathname, "/dev", 4) == 0  || strncmp(pathname, "/proc", 4) == 0) {
    return ret;
  }
  char* parent = get_parent_path(pathname);
  struct GitPath g = {NULL, NULL, NULL};
  if (parent != NULL) {
    g = get_cached_path_info(parent);
  }
  if (ret > 0) {
    char* buf = NULL;
    int len  = 0;
    if (g.version != NULL && g.remote != NULL) {
      len = asprintf(&buf, 
                     "{\"op\":\"open\", \"file\":\"%s\", \"flags\":\"%d\", \"mode\":\"%d\", \"git_version\":\"%s\", \"git_remote\":\"%s\"}\n", 
                     pathname, flags, mode, g.version, g.remote);
    } else {
      len = asprintf(&buf, "{\"op\":\"open\", \"file\":\"%s\", \"flags\":\"%d\", \"mode\":\"%d\"}\n", pathname, flags, mode);
    }
    if (buf != NULL) {
      write_xlog(buf, len);
      free(buf);
    }
  }
  return ret;
}

FILE* internal_fopen(const char* restrict pathname, const char* restrict mode){
  FILE* ret = Real__fopen(pathname, mode);
  if (ENABLE_INTERPOSE == false) {
    return ret;
  }
  if (strncmp(pathname, "/bin", 4) == 0 || strncmp(pathname, "/dev", 4) == 0  || strncmp(pathname, "/proc", 4) == 0) {
    return ret;
  }
  char* parent = get_parent_path(pathname);
  struct GitPath g = {NULL, NULL, NULL};

  if (parent != NULL) {
    g = get_cached_path_info(parent);
  } 
  if (ret > 0) {
    char* buf = NULL;
    int len  = 0;
    if (g.version != NULL && g.remote != NULL) {
      len = asprintf(&buf, 
                     "{\"op\":\"fopen\", \"file\":\"%s\", \"mode\":\"%s\", \"git_version\":\"%s\", \"git_remote\":\"%s\"}\n", 
                     pathname, mode, g.version, g.remote);
    } else {
      len = asprintf(&buf, "{\"op\":\"fopen\", \"file\":\"%s\", \"mode\":\"%s\"}\n", pathname, mode);
    }
    if (buf != NULL) {
      write_xlog(buf, len);
      free(buf);
    }
  }
  return ret;
}

/**************************************************************************/
/*                                                                        */
/*                            Rename Interpose                            */
/*                                                                        */
/**************************************************************************/

INTERPOSE_C(int, rename, (const char* src, const char* dest), (src, dest)) {
  return internal_rename(src, dest);
}


int internal_rename(const char* src, const char* dest){
  struct GitPath srcg = {NULL, NULL, NULL};
  if (ENABLE_INTERPOSE) {
    // we need to poke the src before we call rename.
    // so this is a little bit awkward here
    char* srcparent = get_parent_path(src);
    if (srcparent != NULL) {
      srcg = get_cached_path_info(srcparent);
    }
  }

  int ret = Real__rename(src, dest);
  if (ENABLE_INTERPOSE == false) {
    return ret;
  }

  struct GitPath destg = {NULL, NULL, NULL};
  char* destparent = get_parent_path(dest);
  if (destparent != NULL) {
    destg = get_cached_path_info(destparent);
  }
  if (ret == 0) {
    char* buf = NULL;
    char* srcgbuf = NULL;
    char* destgbuf = NULL;
    if (srcg.version != NULL && srcg.remote != NULL) {
      int len = asprintf(&srcgbuf, ", \"src_git_version\":\"%s\", \"src_git_remote\":\"%s\"", srcg.version, srcg.remote);
    }
    if (destg.version != NULL && destg.remote != NULL) {
      int len = asprintf(&destgbuf, ", \"dest_git_version\":\"%s\", \"dest_git_remote\":\"%s\"", destg.version, destg.remote);
    }
    const char* printsrcg = srcgbuf ? srcgbuf : "";
    const char* printdestg = destgbuf ? destgbuf : "";
    int len = asprintf(&buf, "{\"op\":\"rename\", \"src\":\"%s\", \"dest\":\"%s\"%s%s}\n", src, dest, printsrcg, printdestg);
    if (srcgbuf) free(srcgbuf);
    if (destgbuf) free(destgbuf);
    if (buf != NULL) {
      write_xlog(buf, len);
      free(buf);
    }
  }
  return ret;
}
/**************************************************************************/
/*                                                                        */
/*                             Log management                             */
/*                                                                        */
/**************************************************************************/

int set_xlog_point(const char* fname) {
  int res = Real__open(fname, O_CREAT | O_WRONLY | O_APPEND, 0644);
  if (res == -1) {
    fprintf(stderr, "Cannot open output log file: %s",strerror(errno));
    return errno;
  }
  if (LOG_FILE != NULL) {
    free((void*)LOG_FILE);
  }
  size_t flen = strlen(fname);
  LOG_FILE = malloc(flen + 1);
  memcpy((void*)LOG_FILE, fname, flen + 1);

  LOG_OUTPUT_FD = res;
  return 0;
}

const char* get_xlog_point() {
  return LOG_FILE;
}

int close_xlog_point() {
  if (LOG_OUTPUT_FD >= 0 && 
      LOG_OUTPUT_FD != STDOUT_FILENO && 
      LOG_OUTPUT_FD != STDERR_FILENO) {
    close(LOG_OUTPUT_FD);
  }
  if (LOG_FILE != NULL) {
    free((void*)LOG_FILE);
  }
  LOG_OUTPUT_FD = -1;
  return 0;
}

int write_xlog(const char* s, size_t len) {
  if (LOG_OUTPUT_FD >= 0) {
    return write(LOG_OUTPUT_FD, (void*)s, len);
  }
  return 0;
}

/**************************************************************************/
/*                                                                        */
/*                              Constructor                               */
/*                                                                        */
/**************************************************************************/

bool get_current_executable(char* buf, size_t bufsize) {
#if defined(__APPLE__)
  uint32_t bufsize32 = bufsize;
  if (_NSGetExecutablePath(buf, &bufsize32) == 0) {
    buf[bufsize32] = 0;
    return true;
  }
#elif defined(__WIN32__)
  #error "Not implemented"
#else
  ssize_t b = readlink("/proc/self/exe", buf, bufsize);
  if (b > 0) {
    buf[b] = 0;
    return true;
  }
#endif
  return false;
}

void __attribute__ ((constructor)) xlog_init(void) {
  if (getenv("XTRACE_DISABLE") != NULL) {
      ENABLE_INTERPOSE = false;
      return;
  }
  char buf[4096];
  bool bufok = false;
  bufok = get_current_executable(buf, 4096);
  if (bufok) {
    // black list a bunch of executables and bins
    if (str_ends_with(buf, "/bash") ||
        str_ends_with(buf, "/sh") ||
        str_ends_with(buf, "/dash") ||
        str_ends_with(buf, "/git") ||
        str_starts_with(buf, "/bin") ||
        str_starts_with(buf, "/sbin")) {
      ENABLE_INTERPOSE = false;
      return;
    }
  }
  char* logtarget = getenv("XTRACE_LOG_TARGET");
  if (logtarget != NULL) {
    fprintf(stderr, "XTRACE: LOG_TARGET %s\n", logtarget);
    set_xlog_point(logtarget);
  }
}
