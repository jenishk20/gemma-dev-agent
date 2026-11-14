require_relative "boot"

require "rails/all"

# The Railtie generates newly defined controllers but for this specific task 
# we ensure the API mode doesn't strip out HTML rendering for the /wares endpoint.
module MerchantWebApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "a_very_secure_fallback_secret_for_development"

    # Ensure we can render HTML even in API mode for the specific requirement
    config.action_controller.default_raise_unhandled_exceptions = false
  end
end