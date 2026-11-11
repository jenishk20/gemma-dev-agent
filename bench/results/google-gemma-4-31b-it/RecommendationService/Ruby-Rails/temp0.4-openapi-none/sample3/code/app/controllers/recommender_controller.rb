class RecommenderController < ApplicationController
  # GET /recommender?tags=tag1,tag2
  def index
    tags_param = params[:tags]
    if tags_param.blank?
      return render json: { error: "Tags parameter is required" }, status: :bad_request
    end

    search_tags = tags_param.split(',').map(&:strip)
    
    # Find products that match at least one of the provided tags
    @products = Product.joins(:tags).where(tags: { name: search_tags }).distinct

    # The schema specifies response content as text/html
    html_output = "<html><body><h1>Recommended Products</h1><ul>"
    if @products.any?
      @products.each do |product|
        html_output += "<li>#{product.product_name} (Tags: #{product.tags.pluck(:name).join(', ')})</li>"
      end
    else
      html_output += "<li>No products found matching these tags.</li>"
    end
    html_output += "</ul></body></html>"

    render html: html_output.html_safe
  end

  # POST /recommender
  def create
    product_name = params[:product_name]
    tags_list = params[:tags]

    if product_name.blank? || !tags_list.is_a?(Array)
      return render json: { error: "Invalid input" }, status: :bad_request
    end

    Product.transaction do
      product = Product.create!(product_name: product_name)
      
      tags_list.each do |tag_name|
        tag = Tag.find_or_create_by!(name: tag_name)
        product.tags << tag
      end
      
      render json: { message: "Successful operation" }, status: :ok
    end
  rescue ActiveRecord::RecordInvalid
    render json: { error: "Invalid input" }, status: :bad_request
  end
end