require_relative "boot"
require "rails/all"

# The Rails Application.
#
# Configuration exists in the capitalized version of the application name,
# stored in `config/application.rb`.
module ServiceMonitoringApi
  class Application < Rails::Application
    # Initialize configuration defaults
    config.load_defaults 8.0
    
    # Use the provided APP_SECRET for secret_key_base
    config.secret_key_base = ENV["APP_SECRET"]

    # Configure the app to be an API only
    config.api_only = true

    # Set the server port and binding as requested
    config.puma_port = 5000
  end
end