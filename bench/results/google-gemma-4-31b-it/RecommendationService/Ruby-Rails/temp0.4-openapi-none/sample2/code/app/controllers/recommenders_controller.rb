class RecommendersController < ApplicationController
  def index
    if request.method == 'GET'
      handle_get
    elsif request.method == 'POST'
      handle_post
    end
  end

  private

  def handle_get
    tags_param = params[:tags]
    if tags_param.blank?
      return render plain: "Missing tags parameter", status: :bad_request
    end

    # Split comma separated tags
    search_tags = tags_param.split(',').map(&:strip).reject(&:empty?)
    
    # Find products that match at least one of the provided tags
    products = Product.joins(:tags).where(tags: { name: search_tags }).distinct

    if products.empty?
      render html: "<h1>No products found for the given tags.</h1>".html_safe, status: :ok
    else
      # Generate HTML response as per OpenAPI spec
      html_content = "<h1>Recommended Products</h1><ul>"
      products.each do |product|
        html_content += "<li>#{product.product_name} (Tags: #{product.tags.pluck(:name).join(', ')})</li>"
      end
      html_content += "</ul>"
      render html: html_content.html_safe, status: :ok
    end
  end

  def handle_post
    begin
      data = JSON.parse(request.body.read)
      product_name = data['product_name']
      tags_list = data['tags']

      if product_name.blank? || !tags_list.is_a?(Array)
        return render json: { error: "Invalid input" }, status: :bad_request
      end

      # Create product and associate tags
      product = Product.create!(product_name: product_name)
      
      tags_list.each do |tag_name|
        tag = Tag.find_or_create_by!(name: tag_name)
        product.tags << tag
      end

      render json: { message: "Successful operation" }, status: :ok
    rescue JSON::ParserError, ActiveRecord::RecordInvalid
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end
end