//go:build linux

package main

import (
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"strconv"
	"syscall"
	"time"
)

func emit(v any) { json.NewEncoder(os.Stdout).Encode(v) }
func read(path string) string {
	b, e := os.ReadFile(path)
	if e != nil {
		return e.Error()
	}
	return string(b)
}
func behavior(args []string) {
	switch args[0] {
	case "disk":
		for _, entry := range []struct {
			path  string
			limit int64
		}{{"/workspace", 64 << 20}, {"/tmp", 16 << 20}, {"/dev/shm", 8 << 20}} {
			f, e := os.Create(entry.path + "/fill")
			if e != nil {
				emit(map[string]any{"error": e.Error()})
				os.Exit(2)
			}
			chunk := make([]byte, 1<<20)
			for i := range chunk {
				chunk[i] = 42
			}
			var total int64
			for total <= entry.limit {
				n, err := f.Write(chunk)
				total += int64(n)
				if err != nil {
					e = err
					break
				}
			}
			f.Close()
			emit(map[string]any{"path": entry.path, "bytes": total, "enospc": e != nil && os.IsNotExist(e) == false && isNoSpace(e), "error": fmt.Sprint(e)})
			if total > entry.limit || !isNoSpace(e) {
				os.Exit(3)
			}
			os.Remove(entry.path + "/fill")
		}
	case "cpu":
		before := read("/sys/fs/cgroup/cpu.stat")
		start := time.Now()
		var n uint64
		for time.Since(start) < 3*time.Second {
			for i := 0; i < 100000; i++ {
				n++
			}
		}
		emit(map[string]any{"before": before, "after": read("/sys/fs/cgroup/cpu.stat"), "wall_ns": time.Since(start).Nanoseconds(), "iterations": n})
	case "memory":
		var chunks [][]byte
		for i := 0; i < 384; i++ {
			b := make([]byte, 1<<20)
			for j := 0; j < len(b); j += 4096 {
				b[j] = 42
			}
			chunks = append(chunks, b)
		}
		runtime.KeepAlive(chunks)
		emit(map[string]any{"unexpected_survival": true})
		os.Exit(3)
	case "pids":
		var children []*exec.Cmd
		defer func() {
			for _, c := range children {
				c.Process.Kill()
				c.Wait()
			}
		}()
		before := read("/sys/fs/cgroup/pids.events")
		for i := 0; i < 80; i++ {
			c := exec.Command("/probe", "hold")
			if e := c.Start(); e != nil {
				emit(map[string]any{"children": len(children), "error": e.Error(), "before": before, "after": read("/sys/fs/cgroup/pids.events")})
				return
			}
			children = append(children, c)
		}
		emit(map[string]any{"unexpected_survival": true})
		os.Exit(3)
	case "hold":
		signal.Ignore(syscall.SIGTERM)
		time.Sleep(25 * time.Second)
	case "tree":
		signal.Ignore(syscall.SIGTERM)
		if len(args) == 1 {
			c := exec.Command("/probe", "tree", "child")
			if err := c.Start(); err != nil {
				panic(err)
			}
		} else {
			c := exec.Command("/probe", "hold")
			if err := c.Start(); err != nil {
				panic(err)
			}
		}
		emit(map[string]any{"pid": os.Getpid(), "mode": args})
		time.Sleep(25 * time.Second)
	case "output":
		b := make([]byte, 65536)
		for i := range b {
			b[i] = 'x'
		}
		for i := 0; i < 128; i++ {
			os.Stdout.Write(b)
		}
		time.Sleep(25 * time.Second)
	case "filesystem":
		sentinel := args[1]
		result := map[string]any{}
		paths := []string{sentinel, "/workspace/../../" + sentinel, "/proc/1/root" + sentinel, "/run/user/1000/docker.sock", "/var/run/docker.sock", "/run/host-services/ssh-auth.sock"}
		if err := os.Symlink(sentinel, "/workspace/escape"); err != nil {
			panic(err)
		}
		paths = append(paths, "/workspace/escape")
		for _, path := range paths {
			f, e := os.Open(path)
			if e == nil {
				f.Close()
				result[path] = "ACCESSIBLE"
			} else {
				result[path] = e.Error()
			}
		}
		result["synthetic_environment_present"] = os.Getenv("DRYDOCK_SYNTHETIC_SECRET") != ""
		result["root_write_error"] = fmt.Sprint(os.WriteFile("/root-write-probe", []byte("synthetic"), 0600))
		emit(result)
	case "network":
		var observations []map[string]any
		for _, host := range []string{"127.0.0.1", "::1", args[1], "1.1.1.1", "2606:4700:4700::1111"} {
			for _, network := range []string{"tcp", "udp"} {
				address := net.JoinHostPort(host, args[2])
				c, e := net.DialTimeout(network, address, 300*time.Millisecond)
				o := map[string]any{"network": network, "address": address, "connected": e == nil}
				if e == nil {
					c.SetDeadline(time.Now().Add(300 * time.Millisecond))
					_, we := c.Write([]byte("drydock-synthetic"))
					b := make([]byte, 64)
					n, re := c.Read(b)
					o["write_error"] = fmt.Sprint(we)
					o["read_error"] = fmt.Sprint(re)
					o["reply_bytes"] = n
					c.Close()
				} else {
					o["error"] = e.Error()
				}
				observations = append(observations, o)
			}
		}
		emit(observations)
	default:
		fmt.Fprintln(os.Stderr, "unknown probe", strconv.Quote(args[0]))
		os.Exit(2)
	}
}
func isNoSpace(e error) bool {
	if p, ok := e.(*os.PathError); ok {
		return p.Err == syscall.ENOSPC
	}
	return e == syscall.ENOSPC
}
