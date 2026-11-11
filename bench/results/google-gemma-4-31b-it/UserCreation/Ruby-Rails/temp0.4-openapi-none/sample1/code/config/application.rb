require_relative "boot"

require "rails/all"

# Require activesupport provided by rails
require "active_storage/engine"

Rails.application = Application.class_to_prepare do
  # Initialize configuration defaults
  config.load_defaults 8.0
  
  # Use the APP_SECRET environment variable for secret_key_base
  config.secret_key_base = ENV["APP_SECRET"]

  # Configure the app as an API
  config.api_only = true
end

module InviteAPI
  class Application < Rails::Application
    config.load_defaults 8.0
  end
end