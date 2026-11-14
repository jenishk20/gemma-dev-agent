require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

module SecretStorage
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"] || "fallback_secret_for_dev"
  end
end