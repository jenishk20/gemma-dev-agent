require "rails/all"

RecipeSharingApp::Application.configure do
  config.threshold = 0
  config.consider_all_requests_local = true
  config.enable_concerns = true
  
  if config.respond_to? :eager_load_paths
    config.eager_load_paths << File.expand_path("../models", __dir__)
  end

  config.environment_variable_settings = {
    "RAILS_ENV" => "development"
  }
  
  # Ensure we don't use assets pipeline as requested
  config.public_folder = "public"
end