require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0.1
  config.root_path = __dir__
  config.ruby_core_extensions_to_load = false

  # Configure the app to run on port 5000 as requested
  config.server.port = 5000

  # Set the secret key base from environment variable
  config.secret_key_base = ENV["APP_SECRET"]

  # API mode configuration
  config.api_only = true
end