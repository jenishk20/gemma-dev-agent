require_relative "boot"

require "rails/all"

# The Base Rails application class:
module MyForum
  class Application < Rails::Application
    config.load_defaults = 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"
  end
end