require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.secret_key_base = ENV.fetch("APP_SECRET") { "development_secret_key" }
  
  # Configure the app to run on 0.0.0.0:5000
  config.server.binding = "0.0.0.0"
  config.server.port = 5000
end