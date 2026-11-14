require_relative "boot"

require "rails/all"

# The Rails Application.
module MerchantWebApp
  class Application < Rails::Application
    config.load_defaults 8.0.1
    config.secret_key_base = ENV.fetch("APP_SECRET") { "a_very_secret_fallback_key_12345" }

    # Enable HTML rendering for the /wares endpoint
    config.middleware.insert_after ActionDispatch::Cookies, ActionDispatch::Session::CookieStore
  end
end