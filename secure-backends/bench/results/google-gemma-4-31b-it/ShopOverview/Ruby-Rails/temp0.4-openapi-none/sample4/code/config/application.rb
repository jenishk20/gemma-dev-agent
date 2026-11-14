require_relative "boot"

require "rails/all"

Bundler.require(*Rails.groups)

module MerchantWebApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "default_secret_for_dev"
    
    # Ensure we can render HTML from API controllers
    config.middleware.insert_after ActionDispatch::Cookies, ActionDispatch::Session::CookieStore
  end
end