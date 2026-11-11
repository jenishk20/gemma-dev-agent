require_relative "boot"

require "rails/all"

# Require the rails process element
require "rails/all"

module WikiApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Enable views for the text/html responses required by the OpenAPI spec
    config.middleware.use ActionDispatch::Cookies
    config.middleware.use ActionDispatch::Session::CookieStore
  end
end