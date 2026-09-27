//go:build linux

// m0probe is synthetic qualification material, never a task worker.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"syscall"
)

type observation struct {
	Path           string `json:"path"`
	TotalBytes     uint64 `json:"total_bytes"`
	AvailableBytes uint64 `json:"available_bytes"`
	TotalInodes    uint64 `json:"total_inodes"`
	Flags          int64  `json:"flags"`
	Error          string `json:"error,omitempty"`
}

func main() {
	if len(os.Args) > 1 {
		behavior(os.Args[1:])
		return
	}
	result := map[string]any{"uid": os.Getuid(), "gid": os.Getgid(), "environment": os.Environ()}
	for _, path := range []string{"/proc/self/status", "/proc/self/mountinfo", "/proc/self/cgroup", "/proc/net/route", "/proc/net/ipv6_route", "/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.swap.max", "/sys/fs/cgroup/pids.max"} {
		data, err := os.ReadFile(path)
		if err != nil {
			result[path] = map[string]string{"error": err.Error()}
		} else {
			result[path] = string(data)
		}
	}
	var mounts []observation
	for _, path := range []string{"/", "/workspace", "/tmp", "/dev", "/dev/shm", "/etc/hosts", "/etc/hostname", "/etc/resolv.conf"} {
		var st syscall.Statfs_t
		o := observation{Path: path}
		if err := syscall.Statfs(path, &st); err != nil {
			o.Error = err.Error()
		} else {
			o.TotalBytes = st.Blocks * uint64(st.Bsize)
			o.AvailableBytes = st.Bavail * uint64(st.Bsize)
			o.TotalInodes = st.Files
			o.Flags = st.Flags
		}
		mounts = append(mounts, o)
	}
	result["filesystems"] = mounts
	// Only attempt to open runtime-generated files, never host credentials.
	// No data is written to these files even when opening succeeds.
	writes := map[string]string{}
	for _, path := range []string{"/etc/hosts", "/etc/hostname", "/etc/resolv.conf"} {
		f, err := os.OpenFile(path, os.O_WRONLY, 0)
		if err != nil {
			writes[path] = err.Error()
		} else {
			writes[path] = "WRITABLE"
			f.Close()
		}
	}
	result["runtime_file_write_access"] = writes
	// Synthetic data verifies ordinary scoped writes are possible.
	for _, path := range []string{"/workspace/positive-control", "/tmp/positive-control"} {
		err := os.WriteFile(path, []byte("drydock synthetic\n"), 0600)
		if err != nil {
			result[path] = err.Error()
		} else {
			result[path] = "write succeeded"
		}
	}
	result["probe"] = "profile-inventory"
	// Deliberately report observations only. The independent runner evaluates them.
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(result); err != nil {
		fmt.Fprintln(os.Stderr, strings.TrimSpace(err.Error()))
		os.Exit(1)
	}
}
