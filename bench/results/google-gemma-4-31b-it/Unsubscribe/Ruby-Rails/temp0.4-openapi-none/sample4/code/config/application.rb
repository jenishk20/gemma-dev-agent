require_relative "boot"

require "rails/all"

# The Base Rails application class:
# It's a subclass of Rails::Application.
# Module: UnsubscribeApp
class UnsubscribeApp < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
end