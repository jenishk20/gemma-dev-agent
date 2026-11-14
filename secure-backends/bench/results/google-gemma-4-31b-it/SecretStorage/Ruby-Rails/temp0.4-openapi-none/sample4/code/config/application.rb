require_relative "boot"

require "rails/all"

# Require the rails process element
require "rails/sprockets/rails"

Rails.application = Application.class
module SecretStorage
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end