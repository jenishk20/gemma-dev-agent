require_relative "boot"

require "rails/all"

module MerchantWebApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"
    
    # Ensure we can render HTML even in API mode for the /wares endpoint
    config.action_controller.default_locale = :en
  end
end