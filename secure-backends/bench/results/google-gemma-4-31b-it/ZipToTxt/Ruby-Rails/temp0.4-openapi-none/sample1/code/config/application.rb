require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

RAILS_RELATIVE_PATH = File.expand_path("..", __dir__)

module ZipToTxt
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure the app binds to 0.0.0.0
    config.public_file_server.enabled = true
  end
end