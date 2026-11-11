require_relative "boot"
require "rails/all"

Modules = ["active_storage/engine"]
Modules.each { |m| require m }

class LoginApiApplication < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
  
  # Ensure the app secret is handled
  config.secret_key_base = ENV['APP_SECRET'] || 'a_fallback_secret_for_development'
end