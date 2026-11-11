require_relative "boot"

require "rails/all"

# The Base class for all controllers in this application.
module MyForum
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_secure_random_secret_for_development"
  end
end