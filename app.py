import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config_manager import ConfigManager
from api_client import SonarrRadarrClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize configuration manager
config_manager = ConfigManager("/app/config/configs.yaml")

@app.route('/')
def index():
    """Main page showing all configurations"""
    configs = config_manager.get_all_configs()
    return render_template('index.html', configs=configs)

@app.route('/add_config', methods=['POST'])
def add_config():
    """Add a new Sonarr/Radarr configuration"""
    try:
        name = request.form.get('name', '').strip()
        service_type = request.form.get('service_type')
        ip_address = request.form.get('ip_address', '').strip()
        api_token = request.form.get('api_token', '').strip()
        quality_score = request.form.get('quality_score')
        format_name = request.form.get('format_name', '').strip()
        
        # Validation
        if not name or not service_type or not ip_address or not api_token:
            flash('Name, service type, IP address, and API token are required.', 'error')
            return redirect(url_for('index'))
        
        if service_type not in ['sonarr', 'radarr']:
            flash('Service type must be either Sonarr or Radarr.', 'error')
            return redirect(url_for('index'))
        
        # Convert quality score to int if provided
        if quality_score:
            try:
                quality_score = int(quality_score)
            except ValueError:
                flash('Quality score must be a valid integer.', 'error')
                return redirect(url_for('index'))
        else:
            quality_score = None
        
        # Test API connection
        client = SonarrRadarrClient(ip_address, api_token, service_type)
        if not client.test_connection():
            flash(f'Could not connect to {service_type.title()} API. Please check IP address and API token.', 'error')
            return redirect(url_for('index'))
        
        # Add configuration
        webhook_token = config_manager.add_config(
            name=name,
            service_type=service_type,
            ip_address=ip_address,
            api_token=api_token,
            quality_score=quality_score,
            format_name=format_name
        )
        
        flash(f'Configuration "{name}" added successfully. Webhook token: {webhook_token}', 'success')
        logger.info(f'Added new {service_type} configuration: {name}')
        
    except Exception as e:
        logger.error(f'Error adding configuration: {str(e)}')
        flash(f'Error adding configuration: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/delete_config/<config_id>', methods=['POST'])
def delete_config(config_id):
    """Delete a configuration"""
    try:
        # Get config name for display before deletion
        config = config_manager.get_config(config_id)
        config_name = config.get('name', 'Unknown') if config else 'Unknown'
        
        if config_manager.delete_config(config_id):
            flash(f'Configuration "{config_name}" deleted successfully.', 'success')
            logger.info(f'Deleted configuration: {config_name}')
        else:
            flash(f'Configuration not found.', 'error')
    except Exception as e:
        logger.error(f'Error deleting configuration: {str(e)}')
        flash(f'Error deleting configuration: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/regenerate_token/<config_name>', methods=['POST'])
def regenerate_token(config_name):
    """Regenerate webhook token for a configuration"""
    try:
        new_token = config_manager.regenerate_webhook_token(config_name)
        if new_token:
            flash(f'Webhook token for "{config_name}" regenerated successfully.', 'success')
            logger.info(f'Regenerated webhook token for: {config_name}')
            return jsonify({'success': True, 'token': new_token})
        else:
            flash(f'Configuration "{config_name}" not found.', 'error')
            return jsonify({'success': False, 'error': 'Configuration not found'})
    except Exception as e:
        logger.error(f'Error regenerating token: {str(e)}')
        flash(f'Error regenerating token: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/force_unmonitor/<config_name>', methods=['POST'])
def force_unmonitor(config_name):
    """Regenerate webhook token for a configuration"""
    try:
        config = config_manager.get_config(config_name)
        if config:
            service_type = config.get("service_type")
            if service_type == "sonarr":
                result = process_sonarr_force_unmonitor(config)
                if result:
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Processing failed'})
            elif service_type == "radarr":
                result = process_radarr_force_unmonitor(config)
                if result:
                    return jsonify({'success': True})
                else:
                    return jsonify({'success': False, 'error': 'Processing failed'})
            else:
                flash(f'Unknown service type "{service_type}"', 'error')
                return jsonify({'success': False, 'error': f'Unknown service type "{service_type}"'})
            logger.info(config)
        else:
            flash(f'Configuration "{config_name}" not found.', 'error')
            return jsonify({'success': False, 'error': 'Configuration not found'})
    except Exception as e:
        logger.error(f'Error force unmonitoring: {str(e)}')
        flash(f'Error force unmonitoring: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)})

@app.route('/sonarr', methods=['POST'])
def sonarr_webhook():
    """Handle Sonarr webhook posts"""
    try:
        # Get webhook token from headers
        webhook_token = request.headers.get('X-Webhook-Token')
        if not webhook_token:
            logger.warning('Sonarr webhook received without token')
            return 'Unauthorized', 401
        
        # Find configuration by webhook token
        config = config_manager.get_config_by_token(webhook_token)
        if not config or config['service_type'] != 'sonarr':
            logger.warning(f'Sonarr webhook received with invalid token: {webhook_token}')
            return 'Unauthorized', 401
        
        # Parse webhook data
        webhook_data = request.get_json()
        if not webhook_data:
            logger.warning('Sonarr webhook received without JSON data')
            return 'Bad Request', 400
        
        logger.info(f'Received Sonarr webhook for config: {config["name"]}')
        logger.debug(f'Webhook data: {webhook_data}')
        
        # Process the webhook
        result = process_sonarr_webhook(config, webhook_data)
        
        if result:
            return 'OK', 200
        else:
            return 'Processing failed', 500
            
    except Exception as e:
        logger.error(f'Error processing Sonarr webhook: {str(e)}')
        return 'Internal Server Error', 500

@app.route('/radarr', methods=['POST'])
def radarr_webhook():
    """Handle Radarr webhook posts"""
    try:
        # Get webhook token from headers
        webhook_token = request.headers.get('X-Webhook-Token')
        if not webhook_token:
            logger.warning('Radarr webhook received without token')
            return 'Unauthorized', 401
        
        # Find configuration by webhook token
        config = config_manager.get_config_by_token(webhook_token)
        if not config or config['service_type'] != 'radarr':
            logger.warning(f'Radarr webhook received with invalid token: {webhook_token}')
            return 'Unauthorized', 401
        
        # Parse webhook data
        webhook_data = request.get_json()
        if not webhook_data:
            logger.warning('Radarr webhook received without JSON data')
            return 'Bad Request', 400
        
        logger.info(f'Received Radarr webhook for config: {config["name"]}')
        logger.debug(f'Webhook data: {webhook_data}')
        
        # Process the webhook
        result = process_radarr_webhook(config, webhook_data)
        
        if result:
            return 'OK', 200
        else:
            return 'Processing failed', 500
            
    except Exception as e:
        logger.error(f'Error processing Radarr webhook: {str(e)}')
        return 'Internal Server Error', 500

def process_sonarr_force_unmonitor(config):
    try:
        client = SonarrRadarrClient(config['ip_address'], config['api_token'], 'sonarr')
        to_unmonitor = []
        for serie in client.get_series():
            serie_id = serie.get("id")
            if serie_id is None:
                continue
            for episode in client.get_episodes(serie_id, custom_headers=["includeEpisodeFile=true"]):
                episode_id = episode.get("id")
                if episode_id is None:
                    continue
                episode_monitored = episode.get("monitored", False)
                if not episode_monitored:
                    continue
                episode_has_file = episode.get("hasFile", False)
                if not episode_has_file:
                    continue

                episodeFile = episode.get("episodeFile", {})
                quality_score = episodeFile.get('customFormatScore', 0)
                format_name = [cf["name"] for cf in episodeFile.get('customFormats', []) if cf.get("name")]
                
                # Check if quality criteria is met
                should_unmonitor = False
                
                if config.get('quality_score') is not None:
                    if quality_score >= config['quality_score']:
                        should_unmonitor = True
                        logger.info(f'Quality score {quality_score} meets requirement {config["quality_score"]}')
                
                if config.get('format_name') and format_name:
                    for custom_format in format_name:
                        if config['format_name'].lower() in custom_format.lower():
                            should_unmonitor = True
                            logger.info(f'Format name "{custom_format}" matches requirement "{config["format_name"]}"')
                            break
                if should_unmonitor:
                    to_unmonitor.append(episode_id)

        if len(to_unmonitor) > 0:
            return client.unmonitor_episodes(to_unmonitor)
        return True
        
    except Exception as e:
        logger.error(f'Error processing Sonarr force unmonitor: {str(e)}')
        return False
    
def process_radarr_force_unmonitor(config):
    try:
        client = SonarrRadarrClient(config['ip_address'], config['api_token'], 'radarr')
        for movie in client.get_movies():
            movie_id = movie.get("id")
            if movie_id is None:
                continue
            movie_file_id = movie.get("movieFileId")
            if movie_file_id is None:
                continue
            if not movie.get("monitored", False):
                continue
            movie_file = client.get_movie_file(movie_file_id)
            if movie_file is None:
                continue


            quality_score = movie_file.get('customFormatScore', 0)
            format_name = [cf["name"] for cf in movie_file.get('customFormats', []) if cf.get("name")]
            
            # Check if quality criteria is met
            should_unmonitor = False
            
            if config.get('quality_score') is not None:
                if quality_score >= config['quality_score']:
                    should_unmonitor = True
                    logger.info(f'Quality score {quality_score} meets requirement {config["quality_score"]}')
            
            if config.get('format_name') and format_name:
                for custom_format in format_name:
                    if config['format_name'].lower() in custom_format.lower():
                        should_unmonitor = True
                        logger.info(f'Format name "{custom_format}" matches requirement "{config["format_name"]}"')
                        break
            if should_unmonitor:
                success = client.unmonitor_movie(movie_id)
                if success:
                    logger.info(f'Successfully unmonitored Radarr movie ID: {movie_id}')
                else:
                    logger.error(f'Failed to unmonitor Radarr movie ID: {movie_id}')


        return True
        
    except Exception as e:
        logger.error(f'Error processing Radarr force unmonitor: {str(e)}')
        return False

def process_sonarr_webhook(config, webhook_data):
    """Process Sonarr webhook and unmonitor episodes if criteria met"""
    try:
        # Check if this is a download event
        event_type = webhook_data.get('eventType')
        if event_type != 'Download':
            logger.debug(f'Ignoring Sonarr webhook event type: {event_type}')
            return True
        
        # Get episode and quality information
        episodes = webhook_data.get('episodes', [])
        quality = webhook_data.get('customFormatInfo', {})
        quality_score = quality.get('customFormatScore', 0)
        format_name = [cf["name"] for cf in quality.get('customFormats', []) if cf.get("name")]
        
        # Check if quality criteria is met
        should_unmonitor = False
        
        if config.get('quality_score') is not None:
            if quality_score >= config['quality_score']:
                should_unmonitor = True
                logger.info(f'Quality score {quality_score} meets requirement {config["quality_score"]}')
        
        if config.get('format_name') and format_name:
            for custom_format in format_name:
                if config['format_name'].lower() in custom_format.lower():
                    should_unmonitor = True
                    logger.info(f'Format name "{custom_format}" matches requirement "{config["format_name"]}"')
                    break
        
        if should_unmonitor:
            # Initialize API client
            client = SonarrRadarrClient(config['ip_address'], config['api_token'], 'sonarr')
            
            # Unmonitor each episode
            for episode in episodes:
                episode_id = episode.get('id')
                if episode_id:
                    success = client.unmonitor_episode(episode_id)
                    if success:
                        logger.info(f'Successfully unmonitored Sonarr episode ID: {episode_id}')
                    else:
                        logger.error(f'Failed to unmonitor Sonarr episode ID: {episode_id}')
        
        return True
        
    except Exception as e:
        logger.error(f'Error processing Sonarr webhook: {str(e)}')
        return False

def process_radarr_webhook(config, webhook_data):
    """Process Radarr webhook and unmonitor movie if criteria met"""
    try:
        # Check if this is a download event
        event_type = webhook_data.get('eventType')
        if event_type != 'Download':
            logger.debug(f'Ignoring Radarr webhook event type: {event_type}')
            return True
        
        # Get movie and quality information
        movie = webhook_data.get('movie', {})
        movie_id = movie.get('id')
        quality = webhook_data.get('customFormatInfo', {})
        quality_score = quality.get('customFormatScore', 0)
        format_name = [cf["name"] for cf in quality.get('customFormats', []) if cf.get("name")]
        
        # Check if quality criteria is met
        should_unmonitor = False
        
        if config.get('quality_score') is not None:
            if quality_score >= config['quality_score']:
                should_unmonitor = True
                logger.info(f'Quality score {quality_score} meets requirement {config["quality_score"]}')
        
        if config.get('format_name') and format_name:
            for custom_format in format_name:
                if config['format_name'].lower() in custom_format.lower():
                    should_unmonitor = True
                    logger.info(f'Format name "{custom_format}" matches requirement "{config["format_name"]}"')
                    break
        
        if should_unmonitor and movie_id:
            # Initialize API client
            client = SonarrRadarrClient(config['ip_address'], config['api_token'], 'radarr')
            
            # Unmonitor the movie
            success = client.unmonitor_movie(movie_id)
            if success:
                logger.info(f'Successfully unmonitored Radarr movie ID: {movie_id}')
            else:
                logger.error(f'Failed to unmonitor Radarr movie ID: {movie_id}')
        
        return True
        
    except Exception as e:
        logger.error(f'Error processing Radarr webhook: {str(e)}')
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
