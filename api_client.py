import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SonarrRadarrClient:
    """Custom API client for Sonarr and Radarr"""
    
    def __init__(self, ip_address: str, api_token: str, service_type: str):
        self.ip_address = ip_address.rstrip('/')
        self.api_token = api_token
        self.service_type = service_type.lower()
        self.base_url = f"http://{self.ip_address}/api/v3"
        self.headers = {
            'X-Api-Key': self.api_token,
            'Content-Type': 'application/json'
        }
        
        # Set timeout for requests
        self.timeout = 30
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to Sonarr/Radarr API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f'Making {method} request to: {url}')
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=self.timeout)
            else:
                logger.error(f'Unsupported HTTP method: {method}')
                return None
            
            response.raise_for_status()
            
            # Return JSON response if available
            try:
                return response.json()
            except ValueError:
                # Some endpoints don't return JSON
                return {'status': 'success'}
                
        except requests.exceptions.Timeout:
            logger.error(f'Request timeout for {url}')
        except requests.exceptions.ConnectionError:
            logger.error(f'Connection error for {url}')
        except requests.exceptions.HTTPError as e:
            logger.error(f'HTTP error for {url}: {str(e)}')
        except Exception as e:
            logger.error(f'Unexpected error for {url}: {str(e)}')
        
        return None
    
    def test_connection(self) -> bool:
        """Test connection to Sonarr/Radarr API"""
        try:
            endpoint = 'system/status'
            result = self._make_request('GET', endpoint)
            
            if result:
                logger.info(f'Successfully connected to {self.service_type.title()} at {self.ip_address}')
                return True
            else:
                logger.error(f'Failed to connect to {self.service_type.title()} at {self.ip_address}')
                return False
                
        except Exception as e:
            logger.error(f'Error testing connection: {str(e)}')
            return False
    
    def get_system_status(self) -> Optional[Dict]:
        """Get system status"""
        return self._make_request('GET', 'system/status')
    
    def unmonitor_episode(self, episode_id: int) -> bool:
        """Unmonitor a specific episode in Sonarr"""
        if self.service_type != 'sonarr':
            logger.error('unmonitor_episode called on non-Sonarr client')
            return False
        
        try:
            # First get the episode details
            episode = self._make_request('GET', f'episode/{episode_id}')
            if not episode:
                logger.error(f'Could not retrieve episode {episode_id}')
                return False
            
            # Update the episode to unmonitored
            episode['monitored'] = False
            
            result = self._make_request('PUT', f'episode/{episode_id}', episode)
            
            if result:
                logger.info(f'Successfully unmonitored Sonarr episode {episode_id}')
                return True
            else:
                logger.error(f'Failed to unmonitor Sonarr episode {episode_id}')
                return False
                
        except Exception as e:
            logger.error(f'Error unmonitoring episode {episode_id}: {str(e)}')
            return False
        
    def unmonitor_episodes(self, episode_ids: list[int]) -> bool:
        """Unmonitor a specific episode in Sonarr"""
        if self.service_type != 'sonarr':
            logger.error('unmonitor_episode called on non-Sonarr client')
            return False
        if len(episode_ids) == 0:
            logger.error('There are no episodes')
            return False
        if not isinstance(episode_ids, list):
            logger.error('episode_ids is not list')
            return False
        
        try:
            episodes = {
                "episodeIds": episode_ids,
                "monitored": False
            }
            result = self._make_request('PUT', f'episode/monitor', episodes)
            
            if result:
                logger.info(f'Successfully unmonitored Sonarr episodes {len(episode_ids)}')
                return True
            else:
                logger.error(f'Failed to unmonitor Sonarr episodes {len(episode_ids)}')
                return False
                
        except Exception as e:
            logger.error(f'Error unmonitoring episodes {len(episode_ids)}: {str(e)}')
            return False
    
    def unmonitor_movie(self, movie_id: int) -> bool:
        """Unmonitor a specific movie in Radarr"""
        if self.service_type != 'radarr':
            logger.error('unmonitor_movie called on non-Radarr client')
            return False
        
        try:
            # First get the movie details
            movie = self._make_request('GET', f'movie/{movie_id}')
            if not movie:
                logger.error(f'Could not retrieve movie {movie_id}')
                return False
            
            # Update the movie to unmonitored
            movie['monitored'] = False
            
            result = self._make_request('PUT', f'movie/{movie_id}', movie)
            
            if result:
                logger.info(f'Successfully unmonitored Radarr movie {movie_id}')
                return True
            else:
                logger.error(f'Failed to unmonitor Radarr movie {movie_id}')
                return False
                
        except Exception as e:
            logger.error(f'Error unmonitoring movie {movie_id}: {str(e)}')
            return False
    
    def get_episodes(self, series_id: Optional[int] = None, custom_headers: list[str] = []) -> Optional[list]:
        """Get episodes from Sonarr"""
        if self.service_type != 'sonarr':
            return None
        
        endpoint = 'episode'
        q_added = False
        if series_id:
            endpoint += f'?seriesId={series_id}'
            q_added = True

        for custom_header in custom_headers:
            endpoint += f"{'&' if q_added else '?'}{custom_header}"
            if not q_added:
                q_added = True
        
        result = self._make_request('GET', endpoint)
        if isinstance(result, list):
            return result
        return None
    
    def get_movies(self) -> Optional[list]:
        """Get movies from Radarr"""
        if self.service_type != 'radarr':
            return None
        
        result = self._make_request('GET', 'movie')
        if isinstance(result, list):
            return result
        return None
    
    def get_movie_file(self, movie_id: int = None) -> Optional[dict]:
        """Get movies from Radarr"""
        if self.service_type != 'radarr':
            return None
        if movie_id is None:
            return None
        
        result = self._make_request('GET', f'moviefile/{movie_id}')
        if isinstance(result, dict):
            return result
        return None
    
    def get_series(self) -> Optional[list]:
        """Get series from Sonarr"""
        if self.service_type != 'sonarr':
            return None
        
        result = self._make_request('GET', 'series')
        if isinstance(result, list):
            return result
        return None
