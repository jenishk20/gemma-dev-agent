require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module RecommendationApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
    
    # Ensure we can render HTML even in API mode for the specific requirement
    config.middleware.use Rack::Cors do |app|
      app.cors :options => { :origins => "*", :methods => :all }
    end
  end
end