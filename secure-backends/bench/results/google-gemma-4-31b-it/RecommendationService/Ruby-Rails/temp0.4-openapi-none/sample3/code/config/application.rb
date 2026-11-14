require_relative "boot"

require "rails/all"

modules RecommendationApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_secret_key_for_local_dev"
    config.api_only = true
  end
end