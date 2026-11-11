require_relative "boot"

require "rails/all"

# The Request locale defaults to :en
Rails.application.load_presets

# Initialize config files and establish application settings.
require_relative "environments/application.rb"

module MyCalculator
  class Application < Rails::Application
    # Initialize config files and establish application settings.
    config.load_defaults 8.0
    config.api_only = true
  end
end