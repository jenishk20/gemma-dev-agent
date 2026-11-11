require_relative "boot", path: "__dir__/../"

require "rails/all"

# Require Active Storage engine for file handling if needed
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ZipToTxt
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the server binds to 0.0.0.0 and port 5000 as requested
    config.public_file_server.enabled = ENVIROMENT == 'production'
  end
end