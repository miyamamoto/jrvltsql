"""
32-bit Python worker for UmaConn/NV-Link
This script is called by 64-bit Python via subprocess

Usage:
    python worker_32bit.py <command> [args...]

Commands:
    init                    - Initialize NV-Link
    open <dataspec> <from>  - Open data stream
    read <count>            - Read records
    close                   - Close connection
    status                  - Get connection status

Output:
    JSON to stdout
"""
import sys
import json
import struct

# Verify 32-bit Python
if struct.calcsize("P") * 8 != 32:
    print(json.dumps({
        "success": False,
        "error": "This script requires 32-bit Python",
        "arch": struct.calcsize("P") * 8
    }))
    sys.exit(1)

import win32com.client
import pythoncom
import time


class NVLinkWorker:
    """Worker class for NV-Link operations"""

    def __init__(self):
        self.nvlink = None
        self.initialized = False

    def init(self):
        """Initialize COM and NV-Link"""
        try:
            pythoncom.CoInitialize()

            self.nvlink = win32com.client.Dispatch("NVDTLabLib.NVLink")
            self.nvlink.ParentHWnd = 0

            ret = self.nvlink.NVInit("UNKNOWN")

            if ret == 0:
                self.initialized = True
                return {"success": True, "return_code": ret}
            else:
                return {"success": False, "return_code": ret, "error": f"NVInit failed with code {ret}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def wait_for_download(self, download_count, timeout=300):
        """Wait for download to complete using NVStatus"""
        if not self.initialized or download_count == 0:
            return True

        start_time = time.time()
        while True:
            try:
                status = self.nvlink.NVStatus()
                if status < 0:
                    # Error
                    return False
                if status >= download_count:
                    # Download complete
                    return True
            except:
                pass

            if time.time() - start_time > timeout:
                return False

            time.sleep(0.5)

    def open(self, dataspec, fromtime, option=2, wait_download=True):
        """Open data stream
        
        Args:
            dataspec: Data specification (e.g., "RACE", "0B15")
            fromtime: Start timestamp (YYYYMMDDHHmmss as int or str)
            option: Download option (default=2 for stable operation)
                    1=Differential (has timing issues)
                    2=Full download (recommended)
                    3=Cache only
            wait_download: Whether to wait for download to complete
        """
        if not self.initialized:
            return {"success": False, "error": "Not initialized"}

        try:
            # Convert fromtime to integer if string
            if isinstance(fromtime, str):
                fromtime = int(fromtime)

            result = self.nvlink.NVOpen(dataspec, fromtime, option, 0, 0, '')

            if isinstance(result, tuple):
                ret_code = result[0]
                read_count = result[1] if len(result) > 1 else 0
                dl_count = result[2] if len(result) > 2 else 0
                timestamp = result[3] if len(result) > 3 else ""

                # Wait for download to complete if requested
                if ret_code == 0 and wait_download and dl_count > 0:
                    download_ok = self.wait_for_download(dl_count)
                    if not download_ok:
                        return {
                            "success": False,
                            "return_code": ret_code,
                            "read_count": read_count,
                            "download_count": dl_count,
                            "error": "Download timeout"
                        }

                return {
                    "success": ret_code == 0,
                    "return_code": ret_code,
                    "read_count": read_count,
                    "download_count": dl_count,
                    "timestamp": timestamp
                }
            else:
                return {"success": False, "error": f"Unexpected result: {result}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def read(self, max_records=100):
        """Read records from opened stream using NVGets"""
        if not self.initialized:
            return {"success": False, "error": "Not initialized"}

        try:
            records = []
            count = 0
            buff_size = 50000
            retry_count = 0
            max_retries = 10

            while count < max_records:
                try:
                    # Use NVGets with buffer
                    # Based on kmy-keiba: NVGets(ref obj, size, out filename)
                    buff = bytes(buff_size)
                    result = self.nvlink.NVGets(buff, buff_size, "")

                    if isinstance(result, tuple):
                        ret_code = result[0]

                        if ret_code == 0:
                            # No more data
                            break
                        elif ret_code == -1:
                            # End of current file, continue to next
                            retry_count = 0
                            continue
                        elif ret_code == -3:
                            # Downloading - wait and retry
                            retry_count += 1
                            if retry_count > max_retries:
                                return {
                                    "success": False,
                                    "error": "Download timeout (-3)",
                                    "records_read": count,
                                    "records": records
                                }
                            time.sleep(1)
                            continue
                        elif ret_code < -1:
                            # Other error - but we have some data, return what we have
                            if count > 0:
                                break
                            return {
                                "success": False,
                                "error": f"NVGets error: {ret_code}",
                                "records_read": count,
                                "records": records
                            }
                        else:
                            # Data available (ret_code > 0 means data length)
                            retry_count = 0
                            data = result[1] if len(result) > 1 else None
                            filename = result[2] if len(result) > 2 else ""

                            if data is not None:
                                # Handle different data types
                                if hasattr(data, 'tobytes'):
                                    # memoryview
                                    data_bytes = bytes(data)
                                elif isinstance(data, bytes):
                                    data_bytes = data
                                else:
                                    data_bytes = str(data).encode('utf-8')

                                # Decode data
                                try:
                                    data_str = data_bytes[:ret_code].decode('shift-jis', errors='replace')
                                except:
                                    try:
                                        data_str = data_bytes[:ret_code].decode('cp932', errors='replace')
                                    except:
                                        data_str = data_bytes[:ret_code].hex()

                                # Get record ID (first 2 chars)
                                record_id = data_str[:2] if len(data_str) >= 2 else ""

                                records.append({
                                    "data": data_str[:500],  # Limit data size for JSON
                                    "filename": str(filename).strip() if filename else "",
                                    "record_id": record_id,
                                    "length": ret_code
                                })
                                count += 1
                            else:
                                break
                    else:
                        break

                except Exception as e:
                    # If NVGets fails, try to continue
                    if count > 0:
                        break
                    return {
                        "success": False,
                        "error": f"NVGets exception: {str(e)}",
                        "records_read": count,
                        "records": records
                    }

            return {
                "success": True,
                "records_read": count,
                "records": records
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def status(self):
        """Get connection status"""
        if not self.initialized:
            return {"success": False, "status": -999, "error": "Not initialized"}

        try:
            status = self.nvlink.NVStatus()
            return {"success": True, "status": status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        """Close NV-Link connection"""
        try:
            if self.nvlink is not None:
                self.nvlink.NVClose()
                self.nvlink = None

            self.initialized = False
            pythoncom.CoUninitialize()

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: worker_32bit.py <command> [args...]"
        }))
        sys.exit(1)

    command = sys.argv[1].lower()
    worker = NVLinkWorker()

    try:
        if command == "init":
            result = worker.init()

        elif command == "open":
            if len(sys.argv) < 4:
                result = {"success": False, "error": "Usage: open <dataspec> <fromtime> [option]"}
            else:
                dataspec = sys.argv[2]
                fromtime = int(sys.argv[3])
                option = int(sys.argv[4]) if len(sys.argv) > 4 else 3

                # First init, then open
                init_result = worker.init()
                if init_result["success"]:
                    result = worker.open(dataspec, fromtime, option)
                else:
                    result = init_result

        elif command == "read":
            max_records = int(sys.argv[2]) if len(sys.argv) > 2 else 100

            # Init and open first
            init_result = worker.init()
            if init_result["success"]:
                # Default open for RACE data
                dataspec = sys.argv[3] if len(sys.argv) > 3 else "RACE"
                fromtime = int(sys.argv[4]) if len(sys.argv) > 4 else 20241201000000

                open_result = worker.open(dataspec, fromtime)
                if open_result["success"]:
                    result = worker.read(max_records)
                else:
                    result = open_result
            else:
                result = init_result

        elif command == "status":
            init_result = worker.init()
            if init_result["success"]:
                result = worker.status()
            else:
                result = init_result

        elif command == "close":
            result = worker.close()

        elif command == "test":
            # Full test: init, open, read a few records, close
            result = {"steps": []}

            # Init
            init_result = worker.init()
            result["steps"].append({"init": init_result})

            if init_result["success"]:
                # Open with option=2 (stable full download)
                open_result = worker.open("RACE", 20241201000000, 2)
                result["steps"].append({"open": open_result})

                if open_result["success"]:
                    # Read
                    read_result = worker.read(5)
                    result["steps"].append({"read": read_result})

                # Close
                close_result = worker.close()
                result["steps"].append({"close": close_result})

            result["success"] = all(
                step.get(list(step.keys())[0], {}).get("success", False)
                for step in result["steps"]
            )

        else:
            result = {"success": False, "error": f"Unknown command: {command}"}

    except Exception as e:
        result = {"success": False, "error": str(e)}

    finally:
        # Always try to close
        try:
            worker.close()
        except:
            pass

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
