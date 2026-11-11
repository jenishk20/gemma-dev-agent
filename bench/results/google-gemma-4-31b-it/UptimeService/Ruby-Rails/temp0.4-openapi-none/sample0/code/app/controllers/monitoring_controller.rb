class MonitoringController < ApplicationController
  # POST /heartbeat
  def heartbeat
    service_id = params[:serviceId]
    token = params[:token]

    if service_id.blank? || token.blank?
      return render json: { error: "Invalid request payload" }, status: :bad_request
    end

    # Find or create the service, then update its token and last notification time
    service = Service.find_or_initialize_by(service_id: service_id)
    service.token = token
    service.last_notification = Time.current
    
    if service.save
      head :ok
    else
      render json: { error: "Internal server error" }, status: :internal_server_error
    end
  end

  # POST /services
  def services
    token = params[:token]

    if token.blank?
      return render json: { error: "Invalid request payload" }, status: :bad_request
    end

    # Find all services that match the provided token
    services = Service.where(token: token)
    
    # Map to the requested OpenAPI response format
    response = services.map do |s|
      {
        serviceId: s.service_id,
        lastNotification: s.last_notification&.iso8601
      }
    end

    render json: response, status: :ok
  end
end