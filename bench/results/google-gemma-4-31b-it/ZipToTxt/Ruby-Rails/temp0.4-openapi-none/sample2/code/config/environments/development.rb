require "active_support/core_ext/integer/time"

Rails.application.configure do
  if config.respond_to? :folder
    config.force_ssl = false
  end

  config. ActiveRecord.raise_in_transactional_fixtures = false
  config.active_storage.service = :local
  
  # Disable assets as requested
  config.public_file_server_views = nil
end