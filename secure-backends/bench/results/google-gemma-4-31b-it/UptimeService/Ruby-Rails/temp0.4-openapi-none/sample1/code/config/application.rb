require_relative "boot"

require "rails/all"

# The requested framework requirements
require "active_storage/engine"

module ServiceMonitoringApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Ensure the app uses the provided APP_SECRET if available
    config.secret_key_base = ENV.fetch("APP_SECRET", "a_default_secret_for_development_12345")
  end
end