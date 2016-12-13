/*
 * This file contains the BPF code that is used to count the cpu time 
 * of all the PIDs 
 * */
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

#include <linux/nsproxy.h>
#include <linux/ns_common.h>
// Struct used as key to store the packets of each
// PID seperately.
typedef struct pid_key {
    u64 pid;
    u64 tgid;
    u64 state;
    u64 slot;
} pid_key_t;

#define CONTAINER_PID CONTAINER_PARENT_PID
BPF_HASH(start, u32, u64);
BPF_HASH(cpudist, pid_key_t, u64);
static inline void store_start(u32 tgid, u32 pid, u64 ts)
{
    start.update(&pid, &ts);
}

// update the new timestamp aftet the process has switched state
static inline void update_hist(u32 pid, u32 state, u64 ts)
{
    u64 *tsp = start.lookup(&pid);
    if (tsp == 0)
        return;

    if (ts < *tsp) 
    {
        // Probably a clock issue where the recorded on-CPU event had a
        // timestamp later than the recorded off-CPU event, or vice versa.
        return;
    }
    u64 delta = ts - *tsp;
    delta /= 1000;
    pid_key_t key = {.state=state, .pid = pid, .slot = bpf_log2l(delta)}; 
    cpudist.increment(key);
}

int sched_switch(struct pt_regs *ctx, struct task_struct *prev)
{
    struct task_struct *parent_struct;
    u64 ts = bpf_ktime_get_ns();
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 tgid = pid_tgid >> 32, pid = pid_tgid;
    u32 state = prev->state;
    if ((state & (TASK_RUNNING | TASK_DEAD | TASK_INTERRUPTIBLE) ) == state)
    {
        u32 prev_pid = prev->pid;
        u32 prev_tgid = prev->tgid;
        u64 ppid = 0;
        parent_struct = prev;
        ppid = parent_struct->pid;
        int i=10;
START_LOOP:
        if (--i ==0)
            goto BAIL;
        if(ppid == 1)
            goto BAIL;

        if(ppid == CONTAINER_PID)
        {
            update_hist(prev_pid, state, ts);
            goto BAIL;
        }
        parent_struct = parent_struct->real_parent;
        ppid = parent_struct->pid;        
        goto START_LOOP;
    }
BAIL:
    store_start(tgid, pid, ts);
    return 0;
}
