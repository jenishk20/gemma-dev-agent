require_relative "boot"

require "rails/all"

# The Base class for Active Record models
require "active_model/model"

module CreditCardService
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0

    # Use API only mode
    config.api_only = true

    # Set the secret key base from environment variable
    config.secret_key_base = ENV["APP_SECRET"]
  end
end