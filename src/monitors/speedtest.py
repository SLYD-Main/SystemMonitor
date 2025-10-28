"""Internet speed test monitoring module."""
import speedtest
from typing import Dict, Optional
from datetime import datetime
import threading


class SpeedTestMonitor:
    """Monitor internet connection speed."""

    def __init__(self):
        """Initialize the speed test monitor."""
        self.last_test = None
        self.test_lock = threading.Lock()

    def run_speedtest(self, server_id: Optional[int] = None) -> Dict:
        """
        Run an internet speed test.

        Args:
            server_id: Optional specific server ID to test against

        Returns:
            Dictionary containing speed test results
        """
        with self.test_lock:
            try:
                st = speedtest.Speedtest()

                # Get server list and select best server
                st.get_servers(servers=[server_id] if server_id else [])
                best = st.get_best_server()

                # Run download test
                download_speed = st.download()

                # Run upload test
                upload_speed = st.upload()

                # Get ping
                ping = best['latency']

                # Store results
                self.last_test = {
                    "timestamp": datetime.now().isoformat(),
                    "download": {
                        "bytes_per_second": download_speed,
                        "mbps": download_speed / 1_000_000,
                        "formatted": f"{download_speed / 1_000_000:.2f} Mbps"
                    },
                    "upload": {
                        "bytes_per_second": upload_speed,
                        "mbps": upload_speed / 1_000_000,
                        "formatted": f"{upload_speed / 1_000_000:.2f} Mbps"
                    },
                    "ping": {
                        "ms": ping,
                        "formatted": f"{ping:.2f} ms"
                    },
                    "server": {
                        "id": best['id'],
                        "host": best['host'],
                        "name": best['name'],
                        "country": best['country'],
                        "sponsor": best['sponsor'],
                        "distance": best['d']
                    },
                    "client": {
                        "ip": st.results.client['ip'],
                        "isp": st.results.client['isp'],
                        "country": st.results.client['country']
                    }
                }

                return self.last_test

            except speedtest.ConfigRetrievalError as e:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": "Failed to retrieve speedtest configuration",
                    "details": str(e)
                }
            except speedtest.NoMatchedServers as e:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": "No matched servers found",
                    "details": str(e)
                }
            except Exception as e:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Speed test failed: {type(e).__name__}",
                    "details": str(e)
                }

    def get_last_test(self) -> Optional[Dict]:
        """
        Get the last speed test results.

        Returns:
            Last test results or None if no test has been run
        """
        return self.last_test

    def get_available_servers(self, limit: int = 10) -> Dict:
        """
        Get list of available speedtest servers.

        Args:
            limit: Maximum number of servers to return

        Returns:
            Dictionary containing available servers
        """
        try:
            st = speedtest.Speedtest()
            st.get_servers()

            servers = []
            for server_list in list(st.servers.values())[:limit]:
                for server in server_list:
                    servers.append({
                        "id": server['id'],
                        "host": server['host'],
                        "name": server['name'],
                        "country": server['country'],
                        "sponsor": server['sponsor'],
                        "distance": server['d']
                    })

            return {
                "timestamp": datetime.now().isoformat(),
                "count": len(servers),
                "servers": servers
            }

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def get_client_info(self) -> Dict:
        """
        Get client IP and ISP information.

        Returns:
            Dictionary containing client information
        """
        try:
            st = speedtest.Speedtest()
            config = st.get_config()

            return {
                "timestamp": datetime.now().isoformat(),
                "ip": config['client']['ip'],
                "isp": config['client']['isp'],
                "country": config['client']['country']
            }

        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
