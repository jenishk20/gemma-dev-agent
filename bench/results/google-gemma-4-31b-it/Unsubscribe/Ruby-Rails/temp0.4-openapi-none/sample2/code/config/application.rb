require_relative "boot"

require "rails/all"

# The Base class for all controllers in the application.
module UnsubscribeApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end