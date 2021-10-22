#include "stdio.h"
#include "stdlib.h"
#include "unistd.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <signal.h>


static void sig_int(int signo){
	return;
}
int main(int argc, char* argv[]){
	if(argc < 2){
		printf("Too few arguments!\n");
		exit(1);
	}
	int fd = open(argv[1], O_RDONLY);
	if(fd < 0){
		printf("open failure\n");
		exit(1);
	}

	struct stat st;
	if(fstat(fd, &st) < 0){
		printf("stat error\n");
		exit(1);
	}
	int len = st.st_size;
	printf("size = %d\n", len);
	void* pmap;
	pmap = mmap(0, len, PROT_READ,MAP_SHARED | MAP_POPULATE,fd, 0);

	printf("pmap = 0x%016x\n", pmap);
	if(!pmap){
		printf("map error\n");
		close(fd);
		exit(1);
	}


	for(int i = 0; i < len;i++){
		char c = ((char*)pmap)[i];
	}
	printf("pinning pages...\n");
	if(mlock(pmap, len) == -1){
		printf("mlock error");
		close(fd);
		exit(1);
	}

	printf("done pinning...\n");



	sigset_t set;
	sigemptyset(&set);
	sigaddset(&set,SIGINT);
	int sig;
	signal(SIGINT, sig_int);
	sigwait(&set, &sig);
	printf("unpinning pages...\n");

	if(munlock(pmap, len) < 0){
		printf("munlock error\n");
	}
	munmap(pmap, len);
	close(fd);
	return 0;
}
