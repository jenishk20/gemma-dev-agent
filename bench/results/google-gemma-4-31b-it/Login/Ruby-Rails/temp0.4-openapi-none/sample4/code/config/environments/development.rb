require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set default locale
  config.i18n.default_locale = :en

  # Use cached expanded paths specified by the application.config.cache_expanded_paths
  config. autoload_paths << Rails.root.join("lib")

  # Put your application mode here
  config.cache_store = :memory_cache
  
  # Disable assets as requested
  config.public_file_server.enabled = true
end