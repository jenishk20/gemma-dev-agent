require_relative "boot"

require "rails/all"

# The Rails Application.
#
# Configuration class for the application.
# One of the purposes is to set defaults that work on all environments.
# See https://guides.rubyonrails.org/configuring.html
class ProfileCollection < Rails::Application
  config.load_defaults 8.0
  config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"
  
  # Ensure Active Storage is enabled for the profile photo
  config.active_storage.service = :local
end