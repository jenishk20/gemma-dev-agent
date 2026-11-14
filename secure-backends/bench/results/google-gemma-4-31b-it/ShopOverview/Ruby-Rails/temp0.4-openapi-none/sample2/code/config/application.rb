require_relative "boot"

require "rails/all"

Bundler.require(*Rails.groups)

module MerchantWebApp
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_secret_key_for_development"
    
    # Ensure we can render HTML for the warehouse page
    config.action_controller.default_locale = :en
  end
end