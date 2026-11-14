require_relative "boot"

require "rails/all"

# Require active storage engine as requested
require "active_storage/engine"

module MyForum
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_secret_key_for_development"
  end
end