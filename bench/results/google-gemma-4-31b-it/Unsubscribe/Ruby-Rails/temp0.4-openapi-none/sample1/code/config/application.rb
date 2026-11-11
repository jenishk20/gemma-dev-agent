require_relative "boot"

require "rails/all"

# Require the Rails application
Rails.application = Application.class_new Application
config_file = File.expand_path("config/application.rb", __dir__)

module UnsubscribeApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end