class MonitoringController < ApplicationController
  # POST /heartbeat
  def heartbeat
    service_id = params[:serviceId]
    token = params[:token]

    if service_id.blank? || token.blank?
      return render json: { error: "Invalid request payload" }, status: :bad_request
    end

    # Find or create the service and update its heartbeat
    service = Service.find_or_create_by!(service_id: service_id) do |s|
      s.token = token
    end

    # If the service exists but the token doesn't match, we treat it as unauthorized/invalid
    if service.token != token
      return render json: { error: "Unauthorized" }, status: :bad_request
    end

    service.update!(last_notification_at: Time.current)
    render json: {}, status: :ok
  rescue ActiveRecord::RecordInvalid => e
    render json: { error: e.message }, status: :bad_request
  rescue StandardError => e
    render json: { error: "Internal server error" }, status: :internal_server_error
  end

  # POST /services
  def services
    token = params[:token]

    if token.blank?
      return render json: { error: "Token is required" }, status: :bad_request
    end

    # Find all services that match the provided token
    services = Service.where(token: token).select(:service_id, :last_notification_at)

    # Map to the format required by OpenAPI
    response = services.map do |s|
      {
        serviceId: s.service_id,
        lastNotification: s.last_notification_at&.iso8601
      }
    end

    render json: response, status: :ok
  rescue StandardError => e
    render json: { error: "Internal server error" }, status: :internal_server_error
  end
end