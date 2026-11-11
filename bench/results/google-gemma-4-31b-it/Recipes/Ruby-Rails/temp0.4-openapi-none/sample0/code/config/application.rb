require_relative "boot", require: "rails/all"

# Since we are in an API mode but need some HTML rendering for specific endpoints
# we ensure the necessary engines are loaded.
require "active_storage/engine"

module RecipeSharingApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Allow HTML rendering even in API mode for the specific requirements
    config.middleware.use ActionDispatch::Cookies
    config.middleware.use ActionDispatch::Session::CookieStore
  end
end