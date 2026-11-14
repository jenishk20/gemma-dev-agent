require_relative "boot"

require "rails/all"

# Since we are in an API mode, we don't need active_storage or action_cable engines unless specified
# but we keep the standard Rails API configuration.

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true

  # Use the APP_SECRET env variable for the secret_key_base
  config.secret_key_base = ENV.fetch("APP_SECRET") { "default_secret_for_development" }

  # Configure the app to run on port 5000 as requested
  config.server.port = 5000
end