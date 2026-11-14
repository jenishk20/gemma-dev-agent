class ClicksController < ApplicationController
  # POST /click
  def create
    click = Click.create(timestamp: Time.current)
    if click.persisted?
      render json: {}, status: :created
    else
      render json: { error: 'Invalid request' }, status: :bad_request
    end
  end

  # GET /clicks
  def index
    date_param = params[:date]
    direction = params[:direction]

    if date_param.blank? || direction.blank?
      return render json: { error: 'Missing required parameters' }, status: :bad_request
    end

    unless ["<", ">", "<=", ">="].include?(direction)
      return render json: { error: 'Invalid direction operator' }, status: :bad_request
    end

    begin
      # Parse date to ensure it is valid
      filter_date = Date.parse(date_param).to_time.beginning_of_day
    rescue ArgumentError
      return render json: { error: 'Invalid date format' }, status: :bad_request
    end

    # Construct the query based on the operator
    # We use Arel or raw string interpolation for the operator since it's a limited enum
    clicks = Click.where("#{Click.table_name}.timestamp #{direction} ?", filter_date)

    if clicks.empty?
      render json: { error: 'No clicks found' }, status: :not_found
    else
      render json: clicks.as_json(only: [:id, :timestamp])
    end
  end
end