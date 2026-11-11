class ApplicationController < ActionController::API
  # Ensure the database table exists on startup/request
  before_action :ensure_db_ready

  private

  def ensure_db_ready
    Service.ensure_table_exists
  end
end