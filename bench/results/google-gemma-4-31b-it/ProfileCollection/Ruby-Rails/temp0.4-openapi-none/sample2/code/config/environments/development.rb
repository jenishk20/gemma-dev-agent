require "active_support/core_ext/interior_pointer"

Rails.application.configure do
  # Configure application environment
  config.load_defaults 8.0

  # Use SQLite for development
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
  
  # Allow all requests for the API
  config.middleware.use Rack::Cors do |app|
    app.cors
  end
end