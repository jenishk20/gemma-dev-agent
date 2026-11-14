require_relative "boot"

require "rails/all"

# The Rails Application Server
module SongDownloader
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Ensure the API is configured for JSON
    config.api_only = true
  end
end