require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.server.bind = "0.0.0.0"
  config.server.port = 5000

  # Configure the app for API only
  config.api_only = true
end