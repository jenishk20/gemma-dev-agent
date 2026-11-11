require_relative "boot"

require "rails/all"

# Require the rails process default gems
require "active_model/api"

Bundler.require(*Rails.groups)

module UnsubscribeApp
  class Application < Rails::Application
    # Initialize config for this application
    config.load_defaults 8.0.1

    # Use API only mode
    config.api_only = true
  end
end