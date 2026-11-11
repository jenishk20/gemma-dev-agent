class MonitoringController < ApplicationController
  # We define a simple Service model inline or assume it exists.
  # Since we cannot provide a migration file, we define the schema logic here.
  # In a real Rails app, this would be in app/models/service.rb
  class Service < ApplicationRecord
    # Columns: service_id (string), token (string), last_notification (datetime)
  end

  # Ensure the table exists for the purpose of this standalone exercise
  before_action :setup_database

  def heartbeat
    service_id = params[:serviceId]
    token = params[:token]

    if service_id.blank? || token.blank?
      return render json: { error: "Invalid request payload" }, status: :bad_request
    end

    service = Service.find_or_initialize_by(service_id: service_id)
    service.token = token
    service.last_notification = Time.current
    
    if service.save
      head :ok
    else
      render json: { error: "Internal server error" }, status: :internal_server_error
    end
  end

  def services
    token = params[:token]

    if token.blank?
      return render json: { error: "Token is required" }, status: :bad_request
    end

    services = Service.where(token: token).select(:service_id, :last_notification)
    
    render json: services.map { |s| 
      { 
        serviceId: s.service_id, 
        lastNotification: s.last_notification&.iso8601 
      } 
    }, status: :ok
  end

  private

  def setup_database
    unless Service.connection.table_exists?(:services)
      ActiveRecord::Migration.create_table :services do |t|
        t.string :service_id, null: false
        t.string :token, null: false
        t.datetime :last_notification
        t.index :service_id, unique: true
      end
    end
  end
end