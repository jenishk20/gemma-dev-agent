require_relative "boot"

require "rails/all"

# Require the Rails application configuration
require_relative "environment"

module Recommendation
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_fallback_secret_for_development_purposes_only" }
  end
end