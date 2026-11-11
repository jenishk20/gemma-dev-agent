class MessagesController < ApplicationController
  # GET /messages
  def index
    limit = params[:limit] || 10
    offset = params[:offset] || 0
    sort = params[:sort]&.upcase == 'ASC' ? :asc : :desc

    @messages = Message.order(created_at: sort)
                        .limit(limit)
                        .offset(offset)

    # The OpenAPI schema specifies text/html for the GET response
    render html: render_forum_html(@messages)
  end

  # POST /messages
  def create
    message = Message.new(message_params)
    if message.save
      render json: { status: 'Successful operation' }, status: :ok
    else
      render json: { error: 'Invalid input' }, status: :bad_request
    end
  end

  private

  def message_params
    params.require(:Message).permit(:content, :username)
  end

  def render_forum_html(messages)
    html = "<html><body><h1>MyForum</h1><hr>"
    messages.each do |m|
      html += "<div><strong>#{m.username}</strong>: #{m.content} <small>(#{m.created_at})</small></div><br>"
    end
    html += "</body></html>"
    html
  end
end